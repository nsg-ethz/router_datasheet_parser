import os
import requests
import yaml
import random
import pandas as pd
from typing import Literal, Optional
from markdownify import markdownify as md
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm import tqdm
from load_file import *


# The max/typical power that the router can draw
class Power(BaseModel):
    value: float = Field(description="The maximum or the typical power that the router can draw")
    unit: str = Field(description="The unit of the value mentioned above, usually in W but others could also exist")
    description: Optional[str] = Field(description="The power description that may be associated with the power value (such as the temperature, throughput, ...)")


# Basically the throughput 
class Throughput(BaseModel):
    value: float = Field(description="The value of the throughput of a router")
    unit: str = Field(description="The unit of the value mentioned above, usually in Tbps or Gbps")


# Class to represent the PSU details
class PSU(BaseModel):
    efficiency_rating: Optional[Literal["Bronze", "Silver", "Gold", "Platinum"]] = Field(description="If provided, the rating of the router's Power Supply Unit (PSU)")
    power_rating: Optional[float] = Field(description="How much power a PSU can deliver (unit in watts)")
    number_of_modules: int = Field(description="The number of Power Supply Units (PSUs) used for this router")
    part_number: Optional[str] = Field(description="The part number of this PSU")


# The overall infomation of a router
class RouterInfo(BaseModel):
    pdf_file: str = Field(description="The pdf file storing the information on this router device")
    typical_power_draw: Optional[Power] = Field(description="This is the usual amount of power comsumed by the device under normal operating conditions. It reflects the average power usage when the device is functioning with a typical load.")
    max_power_draw: Optional[Power] = Field(description="This is the maximum amount of power the router can consume, usually measured under peak load or stressful conditions. It represents the highest power demand the device will require, typically when all resources are being utilized to their fullest capacity.")
    max_throughput: Optional[Throughput] = Field(description="The maximum throughput or the bandwidth used in the url, usually in the unit of Tbps or Gbps")
    psu: Optional[PSU] = Field(description="The Power Supplier Unit(PSU) related data")


class RouterDate(BaseModel):
    release_date: str = Field(description="The date when the product was first made available to the public in YYYY-MM-DD format. It marks the start of the product's lifecycle on the market")
    end_of_sale: str = Field(description="The last date on which the product could be purchased in YYYY-MM-DD format. After this date, the product is no longer available for sale from the manufacturer")
    end_of_support: str = Field(description="The final date which the manufacturer will provide support in YYYY-MM-DD format. After this date, official support ends, and the product is considered 'en of life'")


def is_model_without_url(model, routers_without_url_csv):
    df = pd.read_csv(routers_without_url_csv)
    return model in df["model"].values


def process_url_llm(router_name, url):
    """
    Use the OpenAI API to help us extract the information based on provided URL.
    
    Parameters:
        router_name:    The router name
        url:            The URL of this model
    """
    PERSONA         =   "You are a knowledgeable network engineer with expertise in router technologies."
    HIGH_LEVEL_TASK =   "You are tasked with gathering detailed information on various routers within your network." \
                        "Your objective is to scan the provided URLs that contain router data and extract relevant information about the associated router." 
    LOW_LEVEL_TASK  =   lambda router_name: f"I will give you the URL containing the information you are after. You are looking for the data relevant only to router {router_name}" \
                        "Your task is to use your expertise and the URL I provided to try to extract the information and fill out the fields of the given structure. " \
                        "If the information is not present, you can leave the field empty. If you are unsure, leave the field empty.\n" \
                        "Only use the information contained in the URL." \
                        "Please note that the URL is the router series, meaning that it will contain the info of other routers in the same series.\n" \
                        "For example, on the url of router 8201-32FH, it will contain information of Cisco 8201-SYS.\n" \
                        "Your goal is to avoid extracting info of Cisco 8201-SYS and pay attention to only 8202-32FH." \
                        "For the pdf file, please return to the full URL links." \
                        "For the typical/max power draw, the typical power draw is typically smaller than the power draw in theory. \n"


    system_prompt = lambda router_name: "\n".join([PERSONA, HIGH_LEVEL_TASK, LOW_LEVEL_TASK(router_name)])

    client = OpenAI()
    html_content = requests.get(url).text

    # Transfer the HTML to MD to reduce the number of tokens
    # encoding = tiktoken.encoding_for_model("gpt-4o")
    markdown_content = md(html_content)
    os.makedirs("../result/markdown", exist_ok=True)
    with open(f"../result/markdown/{router_name}.md", "w") as f:
        f.write(markdown_content)

    # Call the OpenAI API
    try:
        completion = client.beta.chat.completions.parse(
            # This model is only for debug. It will be changed to a more powerful model
            # model = "gpt-4o-mini",
            model = "gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt(router_name)
                },
                {
                    "role": "user",
                    "content": markdown_content
                }
            ],
            response_format=RouterInfo,
        )

        output = completion.choices[0].message.parsed
        parsed_router_url_llm = output.model_dump(mode="yaml")

        # Extract units
        return parsed_router_url_llm
    
    except Exception as e:
        print("Error: ", e)
        pass


def process_router_date_llm(router_name):
    """
    Use the OpenAI API to help us extract the date information.
    
    Parameters:
        router_name:    The router name
    """
    PERSONA         =   "You are a knowledgeable network engineer with expertise in router technologies."
    HIGH_LEVEL_TASK =   "You are tasked with gathering the date information on various routers within your own kownledge base or online information." \
                        "Your objective is to search the provided router model name and then find the useful information about the requested dates" 
    LOW_LEVEL_TASK  =   lambda router_name: f"I will give you the router manufacturer and model name. You are looking for the date relevant only to router {router_name}" \
                        "Your task is to use your expertise to try to extract the date information and fill out the fields of the given structure. " \
                        "The source can be anything, e.g., the url of this product, the information published online, etc." \
                        "If the information is not present, you can leave the field empty. If you are unsure, leave the field empty.\n" \
    
    # Call the OpenAI API
    client = OpenAI()
    system_prompt = lambda router_name: "\n".join([PERSONA, HIGH_LEVEL_TASK, LOW_LEVEL_TASK(router_name)])

    try:
        completion = client.beta.chat.completions.parse(
            # This model is only for debug. It will be changed to a more powerful model
            # model = "gpt-4o-mini",
            model = "gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt(router_name)
                },
                {
                    "role": "user",
                    "content": "Let's find the date mentioned in the prompt."
                }
            ],
            response_format=RouterDate,
        )

        output = completion.choices[0].message.parsed
        parsed_router_date_llm = output.model_dump(mode="yaml")
        print("parsed_router_date_llm: ", parsed_router_date_llm)

        # Extract units
        return parsed_router_date_llm
    
    except Exception as e:
        print("Error: ", e)
        pass


if __name__ == "__main__":

    result_directory = "../result/Cisco/"
    routers_without_url = "../result/routers_without_url.csv"

    router_names = [name for name in os.listdir(result_directory) if os.path.isdir(os.path.join(result_directory, name))]
    random.seed(42)
    random_selection = random.sample(router_names, 10)

    for router_name in tqdm(random_selection):
        print("router name: ", router_name)
        # This router contains the URL
        if not is_model_without_url(router_name, routers_without_url):
            print("router name: ", router_name)
            filtered_netbox_file = result_directory + router_name + "/" + router_name + "_filtered_netbox.yaml"
            url = load_yaml(filtered_netbox_file)["url"]
            parsed_router_url_llm = process_url_llm(router_name, url)

            # Write the info parsed by LLM to a yaml file and store it in the same directory of its associated filtered_network.yaml
            router_result_dirctory = result_directory + router_name + "/"
            router_url_llm_file = router_name + "_url_llm.yaml"
            save_yaml(parsed_router_url_llm, router_result_dirctory+router_url_llm_file)
        
        router_result_dirctory = result_directory + router_name + "/"
        router_date_llm_file = router_name + "_date_llm.yaml"
        parsed_router_date_llm = process_router_date_llm(router_name)
        save_yaml(parsed_router_date_llm, router_result_dirctory+router_date_llm_file)