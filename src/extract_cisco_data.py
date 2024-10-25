import os
import re
import requests
import yaml
from typing import Literal, Optional
from markdownify import markdownify as md
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm import tqdm


# Class to represent the PSU details
class PSU(BaseModel):
    efficiency_rating: Optional[Literal["Bronze", "Silver", "Gold", "Platinum"]] = Field(description="If provided, the rating of the router's Power Supply Unit (PSU)")
    power_rating: Optional[float] = Field(description="How much power a PSU can deliver (unit in watts)")
    number_of_modules: int = Field(description="The number of Power Supply Units (PSUs) used for this router")
    part_number: Optional[str] = Field(description="The part number of this PSU")


# The max/typical power that the router can draw
class Power(BaseModel):
    value: int = Field(description="The maximum or the typical power that the router can draw (unit in watts)")
    description: Optional[str] = Field(description="The power description that may be associated with the power value (such as the temperature, throughput, ...)")


# The overall infomation of a router
class RouterData(BaseModel):
    pdf_file: str = Field(description="The pdf file storing the information on this router device")
    typical_power_draw: Optional[Power] = Field(description="The typical power consumption of the router")
    max_power_draw: Optional[Power] = Field(description="The maximum power consumption of the router")
    max_throughput: float = Field(description="The maximum throughput or the bandwidth used in the url, usually in the unit of Tbps")
    release_date: Optional[str] = Field(description="Day the router series was released (YYYY-MM-DD format)")
    end_of_sale: Optional[str] = Field(description="The last day which this router was sold (YYYY-MM-DD format)")
    end_of_support: Optional[str] = Field(description="The last day this router was officially supported (YYYY-MM-DD format)")
    psu: Optional[PSU] = Field(description="The Power Supplier Unit(PSU) related data")


def filter_info_from_netbox(filename):

    netbox_info = {}

    with open(filename, "r") as f:
        content = yaml.safe_load(f)
        print("content: ", content)

        netbox_info["manufacturer"] = content["manufacturer"]
        netbox_info["model"] = content["model"]
        netbox_info["slug"] = content["slug"]
        netbox_info["part_number"] = content["part_number"]
        netbox_info["u_height"] = content["u_height"]

        # URL
        url = content.get("comments")
        url_pattern = re.compile(r'https?://[^\s]+')
        url_match = url_pattern.search(str(url))
        if url_match:
            url = url_match.group()[:-1]
        else:
            url = None
            # Log the files which don't have the url
            with open("../result/routers_without_url.csv", "a") as router_without_url:
                router_without_url.write(f"{filename}\n")

        # PSU



def data_parsing(router_dir):

    PERSONA         =   "You are a knowledgeable network engineer with expertise in router technologies."
    HIGH_LEVEL_TASK =   "You are tasked with gathering detailed information on various routers within your network." \
                        "Your objective is to scan the provided URLs that contain router data and extract relevant information about the associated router." 
    LOW_LEVEL_TASK  =   lambda name: f"I will give you the URL containing the information you are after. You are looking for the data relevant only to router {name}" \
                        "Your task is to use your expertise and the URL I provided to try to extract the information and fill out the fields of the given structure. " \
                        "If the information is not present, you can leave the field empty. If you are unsure, leave the field empty.\n" \
                        "Only use the information contained in the URL." \
                        "Please note that the URL is the router series, meaning that it will contain the info of other routers in the same series.\n" \
                        "For example, on the url of router 8201-32FH, it will contain information of Cisco 8201-SYS.\n" \
                        "For the pdf file, please return to the full URL links." \
                        "Your goal is to avoid grapping info of Cisco 8201-SYS and pay attention to only 8202-32FH."

    # For future reference, can build Lambdas into this using: TEXT_AMOUNT = lambda amount: f'text {amount}'
    system_prompt = lambda name: "\n".join([PERSONA, HIGH_LEVEL_TASK, LOW_LEVEL_TASK(name)])

    client = OpenAI()

    # Create an empty file for storing the routers without the URL
    with open("../result/routers_without_url.csv", "w") as router_without_url:
        pass
    
    files = [f for f in os.listdir(router_dir) if os.path.isfile(os.path.join(router_dir, f))]
    # files = ["8201-24H8FH.yaml", "8201-32FH.yaml", "ASR-920-24SZ-M.yaml", "2951-ISR.yaml", "AIR-AP1562D-B-K9.yaml"]
    files = ["8201-24H8FH.yaml"]

    for filename in tqdm(files):

        model = filename.split('/')[-1].split('.')[0]
        print(f"model: {model}")
        url_pattern = re.compile(r'https?://[^\s]+')
        
        # Open and load the yaml file
        with open(os.path.join(router_dir, filename), 'r') as f:
            content = yaml.safe_load(f)
            url = content.get("comments")
        url_match = url_pattern.search(str(url))
        if url_match:
            url = url_match.group()[:-1]
        else:
            url = None
            # Log the files which don't have the url
            with open("../result/routers_without_url.csv", "a") as router_without_url:
                router_without_url.write(f"{filename}\n")
            continue

        print(f"url: {url}")
        html_content = requests.get(url).text

        # Transfer the HTML to MD to reduce the number of tokens
        # encoding = tiktoken.encoding_for_model("gpt-4o")
        markdown_content = md(html_content)
        os.makedirs("../result/markdown", exist_ok=True)
        with open(f"../result/markdown/{model}.md", "w") as f:
            f.write(markdown_content)
        
        output_dict = {}
        output_dict["manufacturer"] = content.get("manufacturer")
        output_dict["model"] = content.get("model")
        output_dict["slug"] = content.get("slug")
        output_dict["part_number"] = content.get("part_number")
        output_dict["u_height"] = content.get("u_height")
        output_dict["url"] = url

        # Call the OpenAI API
        try:
            completion = client.beta.chat.completions.parse(
                temperature=0,
                model = "gpt-4o-mini-2024-07-18",
                # model = "gpt-4o-2024-08-06",
                messages=[ 
                    {
                        "role": "system", 
                        "content": system_prompt(model)
                    },
                    {
                        "role": "user",
                        "content": markdown_content
                    }
                ],
                response_format=RouterData,
            )

            # output is the result coming from the GPT
            output = completion.choices[0].message.parsed

            # Dump the model to a dictionary with yaml-compatible formatting
            output = output.model_dump(mode='yaml')
            print(f"output: {output}")

            output_dict["pdf_file"] = output["pdf_file"]
            output_dict["release_date"] = output["release_date"]
            output_dict["end_of_sale"] = output["end_of_sale"]
            output_dict["end_of_support"] = output["end_of_support"]
            output_dict["max_throughput(Tbps)"] = output["max_throughput"]

            # Max and typical power draw
            output_dict["max_power_draw(W)"] = output["max_power_draw"]
            output_dict["typical_power_draw(W)"] = output["typical_power_draw"]

            # PSU related
            output_dict["PSU"] = output["psu"]

        except Exception as e:
            print(f"Error: {e}")
            pass
    
        # Write the output_dict into the new yaml file
        os.makedirs("../result/yaml", exist_ok=True)
        yaml_name = "../result/yaml/" + filename
        with open(yaml_name, "w") as yaml_file:
            yaml.dump(output_dict, yaml_file, default_flow_style=False, sort_keys=False)


if __name__ == "__main__":

    router_dir = "../dataset/Cisco/"

    # Create an empty file for storing the routers without the URL
    with open("../result/routers_without_url.csv", "w") as router_without_url:
        pass

    for file in tqdm(files):
        print("file: ", file)
        filter_info_from_netbox(os.path.join(router_dir, file))
        break
