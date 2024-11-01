import os
import requests
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
    datasheet_pdf: str = Field(description="The pdf file storing the information on this router device.")
    typical_power_draw: Optional[Power] = Field(description="This is the usual amount of power comsumed by the device under normal operating conditions. It reflects the average power usage when the device is functioning with a typical load.")
    max_power_draw: Optional[Power] = Field(description="This is the maximum amount of power the router can consume, usually measured under peak load or stressful conditions. It represents the highest power demand the device will require, typically when all resources are being utilized to their fullest capacity.")
    max_poe_draw: Optional[Power] = Field(description="This is the maximum PoE consumption. PoE can deliver data and power over a single Ethernet cable.")
    max_throughput: Optional[Throughput] = Field(description="The maximum throughput or the bandwidth used in the url, usually in the unit of Tbps or Gbps")
    psu: Optional[PSU] = Field(description="The Power Supplier Unit(PSU) related data")


class DateReference(BaseModel):
    date: str = Field(description="A date format in YYYY-MM-DD")
    reference: str = Field(description="A reference link or source indicating where this date is found online")


class RouterDate(BaseModel):
    release_date: Optional[DateReference] = Field(description="The date when the product was first made available to the public. It marks the start of the product's lifecycle on the market")
    end_of_sale: Optional[DateReference] = Field(description="The last date on which the product could be purchased. After this date, the product is no longer available for sale from the manufacturer")
    end_of_support: Optional[DateReference] = Field(description="The final date which the manufacturer will provide support. After this date, official support ends, and the product is considered 'end of life'")


def is_model_without_url(model, routers_without_url_csv):
    df = pd.read_csv(routers_without_url_csv)
    return model in df["model"].values


def process_datasheet_url_llm(router_name, url):
    """
    Use the OpenAI API to help us extract the information based on provided URL.
    
    Parameters:
        router_name:    The router name
        url:            The URL of this model
    """
    print("url : ", url)
    prompt_file = "process_datasheet_prompt.txt"
    components = load_prompt_components(prompt_file, router_name)
    
    # Define the system_prompt
    system_prompt = "\n".join([
        components["PERSONA"],
        components["HIGH_LEVEL_TASK"],
        components["LOW_LEVEL_TASK"]
    ])

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
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": markdown_content
                }
            ],
            response_format=RouterInfo,
        )

        output = completion.choices[0].message.parsed
        print("output: \n", output)
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
    
    prompt_file = "process_router_date_prompt.txt"
    components = load_prompt_components(prompt_file, router_name)
    
    # Define the system_prompt
    system_prompt = "\n".join([
        components["PERSONA"],
        components["HIGH_LEVEL_TASK"],
        components["LOW_LEVEL_TASK"]
    ])

    client = OpenAI()

    try:
        completion = client.beta.chat.completions.parse(
            # This model is only for debug. It will be changed to a more powerful model
            model = "gpt-4o-mini",
            # model = "gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
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
    random_selection = random.sample(router_names, 5)

    for router_name in tqdm(random_selection):
    
        # This router contains the URL
        if not is_model_without_url(router_name, routers_without_url):
            print("=====================================================")
            print("router name: ", router_name)
            filtered_netbox_file = result_directory + router_name + "/" + router_name + "_filtered_netbox.yaml"
            url = load_yaml(filtered_netbox_file)["datasheet_url"]
            parsed_router_url_llm = process_datasheet_url_llm(router_name, url)

            # Write the info parsed by LLM to a yaml file and store it in the same directory of its associated filtered_network.yaml
            router_result_dirctory = result_directory + router_name + "/"
            router_url_llm_file = router_name + "_url_llm.yaml"
            save_yaml(parsed_router_url_llm, router_result_dirctory+router_url_llm_file)
        
        # Write the date into the yaml
        router_result_dirctory = result_directory + router_name + "/"
        router_date_llm_file = router_name + "_date_llm.yaml"
        parsed_router_date_llm = process_router_date_llm(router_name)
        save_yaml(parsed_router_date_llm, router_result_dirctory+router_date_llm_file)
