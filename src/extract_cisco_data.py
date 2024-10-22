import os
import re
import requests
import yaml
import tiktoken
from typing import Literal, Optional
from markdownify import markdownify as md
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm import tqdm

class Power(BaseModel):
    value: int = Field(description="The value in watts")
    power_description: Optional[str] = Field(description="The power description that may be associated with the power value (such as the temperature, throughput, ...)")

class RouterData(BaseModel):
    datasheet_file: str = Field(description="The pdf file stroing the information on this router device")
    typical_power_draw: Optional[Power] = Field(description="The typical power consumption of the router")
    max_power_draw: Optional[Power] = Field(description="The maximum power consumption of the router")
    max_throughput: float = Field(description="The maximum throughput or the bandwidth used in the url, typically in the unit of Tbps")
    # The date has to be a string required by the API: https://community.openai.com/t/getting-a-date-for-a-function/759592
    release_date: Optional[str] = Field(description="Day the router series was released (YYYY-MM-DD format)")
    end_of_sale: Optional[str] = Field(description="The last day which this router was sold (YYYY-MM-DD format)")
    end_of_support: Optional[str] = Field(description="The last day this router was officially supported (YYYY-MM-DD format)")
    num_psu: int = Field(description="The number of Power Supply Units (PSUs)")
    psu_rating: Optional[Literal["Bronze", "Silver", "Gold", "Platinum"]] = Field(description="If provided, the rating of the router's Power Supply Unit (PSU)")


def data_parsing(router_dir):

    PERSONA         =   "You are a knowledgeable network engineer with expertise in router technologies."
    HIGH_LEVEL_TASK =   "You are tasked with gathering detailed information on various routers within your network." \
                        "Your objective is to scan provided URLs that contain router data and extract relevant information about the PSUs." 
    LOW_LEVEL_TASK  =   lambda name: f"I will give you the URL containing the information you are after. You are looking for the data relevant only to router {name}" \
                        "Your task is to use your expertise and the URL I provided to try to extract the information and fill out the fields of the given structure. " \
                        "If the information is not present, you can leave the field empty. If you are unsure, leave the field empty.\n" \
                        "Only use the information contained in the URL." \
                        "Please pay attention to that the URL is the router series, meaning that it will contain the info of other routers in the same series.\n" \
                        "For example, on the url of router 8201-32FH, it will contain information of Cisco 8201-SYS.\n" \
                        "Your goal is to avoid grapping info of Cisco 8201-SYS and pay attention to only 8202-32FH."

    # For future reference, can build Lambdas into this using: TEXT_AMOUNT = lambda amount: f'text {amount}'
    system_prompt = lambda name: "\n".join([PERSONA, HIGH_LEVEL_TASK, LOW_LEVEL_TASK(name)])

    client = OpenAI()
    
    # files = [f for f in os.listdir(router_dir) if os.path.isfile(os.path.join(router_dir, f))]
    files = ["8201-24H8FH.yaml", "8201-32FH.yaml", "ASR-920-24SZ-M.yaml"]
    # files = ["8201-24H8FH.yaml"]

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
                # model = "gpt-4o-mini",
                model = "gpt-4o-2024-08-06",
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

            # Get the output from your API call
            output = completion.choices[0].message.parsed

            # Dump the model to a dictionary with JSON-compatible formatting
            output = output.model_dump(mode='yaml')
            # print(f"output: {output}")

            # Sometimes, the datasheet(pdf) is not shown correctly
            output_dict["datasheet_file"] = output["datasheet_file"]
            if not output_dict["datasheet_file"].startswith('https:'):
                output_dict["datasheet_file"] = "https://www." + str(content.get("manufacturer")).lower() + ".com" + output_dict["datasheet_file"]
            output_dict["release_date"] = output["release_date"]
            output_dict["end_of_sale"] = output["end_of_sale"]
            output_dict["end_of_support"] = output["end_of_support"]
            output_dict["max_throughput(Tbps)"] = output["max_throughput"]

            # Max and typical power draw
            output_dict["maximum_power_draw"] = output["max_power_draw"]
            output_dict["typical_power_draw"] = output["typical_power_draw"]

            # PSU related
            output_dict["PSU"] = {}
            output_dict["PSU"]["efficiency_rating"] = output["psu_rating"]
            output_dict["PSU"]["power_rating(W)"] = None # Currently leave it blank

            # Some files contain the power-ports
            if content.get("power-ports"):
                output_dict["PSU"]["number_of_modules"] = len(content.get("power-ports", []))
                output_dict["PSU"]["part_number"] = content.get("power-ports")[0]["type"]
            
            # Some files contain the model-bays
            elif content.get("module-bays"):
                output_dict["PSU"]["number_of_modules"] = len(content.get("module-bays", []))
                output_dict["PSU"]["part_number"] = None
            
            # Some don't contain both
            else:
                output_dict["PSU"]["number_of_modules"] = output["num_psu"]
                output_dict["PSU"]["part_number"] = None

        except Exception as e:
            print(f"Error: {e}")
            pass
    
        # Write the output_dict into the new yaml file
        os.makedirs("../result/yaml", exist_ok=True)
        yaml_name = "../result/yaml/" + filename
        with open(yaml_name, "w") as yaml_file:
            yaml.dump(output_dict, yaml_file, default_flow_style=False, sort_keys=False)

if __name__ == "__main__":

    router_dir = "../dataset/Selected_Router/" # TODO: Selected_Router is only for testing purpose, it will be modified later
    data_parsing(router_dir)
