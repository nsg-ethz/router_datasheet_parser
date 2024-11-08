import os
import requests
import random
import pandas as pd
from typing import Literal, Optional
from markdownify import markdownify as md
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
    efficiency_rating: Optional[Literal["Bronze", "Silver", "Gold", "Platinum"]] = Field(description="The 80 Plus certification level indicating the power supply unit's efficiency, with ratings from Bronze to Platinum, where higher levels signify greater energy efficiency.")
    power_rating: Optional[Power] = Field(description="How much power a PSU can deliver")
    number_of_modules: int = Field(description="The number of Power Supply Units (PSUs) used for this router")
    part_number: Optional[str] = Field(description="The part number of this PSU")


# The overall infomation of a router
class RouterInfo(BaseModel):
    series: str = Field(description="The series which this router model belong to.")
    datasheet_pdf: str = Field(description="The pdf file storing the information on this router device.")
    max_throughput: Optional[Throughput] = Field(description="The maximum throughput or the bandwidth used in the url, usually in the unit of Tbps or Gbps")
    typical_power_draw: Optional[Power] = Field(description="This is the usual amount of power comsumed by the device under normal operating conditions. It reflects the average power usage when the device is functioning with a typical load")
    max_power_draw: Optional[Power] = Field(description="This is the maximum amount of power the router can consume, usually measured under peak load or stressful conditions. It represents the highest power demand the device will require, typically when all resources are being utilized to their fullest capacity")
    is_poe_capable: bool = Field(description="A boolean value. If this router is poe_capable, then return true, otherwise return false")
    max_poe_draw: Optional[Power] = Field(description="This is the maximum Power over Ethernet consumption. PoE enables network cables to supply both data and electrical power to devices")
    psu: Optional[PSU] = Field(description="The Power Supplier Unit(PSU) related data")


class ValueReference(BaseModel):
    value: str = Field(description="A value based on a specific class. In our current case, it can be either date of router_type")
    reference: str = Field(description="A reference link or source indicating where this date is found online")


class RouterDate(BaseModel):
    release_date: Optional[ValueReference] = Field(description="The date when the product was first made available to the public in the format of YYYY-MM-DD. It marks the start of the product's lifecycle on the market")
    end_of_sale: Optional[ValueReference] = Field(description="The last date on which the product could be purchased in the format of YYYY-MM-DD. After this date, the product is no longer available for sale from the manufacturer")
    end_of_support: Optional[ValueReference] = Field(description="The final date which the manufacturer will provide support in the format of YYYY-MM-DD. After this date, official support ends, and the product is considered 'end of life'")


class RouterType(BaseModel):
    router_type: Optional[ValueReference] = Field(description="The category of the router, such as 'edge', 'core', 'distribution', among others.")


class RouterURL(BaseModel):
    router_url: Optional[str] = Field(description="The official URL for the router, providing detailed product information and specifications.")


def is_model_without_url(model, routers_without_url_csv):
    df = pd.read_csv(routers_without_url_csv)
    return model in df["model"].values


def process_datasheet_with_url_llm(router_name, url):
    """
    Use the OpenAI API to help us extract the information based on provided URL.
    
    Parameters:
        router_name:    The router name
        url:            The URL of this model
    """
    prompt_file = "process_datasheet_with_url_prompt.txt"
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

    print("markdown_content: ", type(markdown_content))
    # Call the OpenAI API
    try:
        completion = client.beta.chat.completions.parse(
            # model = "gpt-4o-mini",
            temperature = 0,
            model = "gpt-4o",
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
        parsed_router_url_llm = output.model_dump(mode="yaml")

        # Extract units
        return parsed_router_url_llm
    
    except Exception as e:
        print("Error: ", e)
        pass


def process_datasheet_without_url_llm(router_name):

    prompt_file = "process_datasheet_without_url_prompt.txt"
    components = load_prompt_components(prompt_file, router_name)

    # Define the system_prompt
    system_prompt = "\n".join([
        components["PERSONA"],
        components["HIGH_LEVEL_TASK"],
        components["LOW_LEVEL_TASK"]
    ])

    client = OpenAI()

    # Call the OpenAI API
    try:
        completion = client.beta.chat.completions.parse(
            temperature = 0,
            model = "gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": "Let's find the router information based on the prompt"
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

    prompt_file = "process_router_date_prompt.txt"
    components = load_prompt_components(prompt_file, router_name)

    system_prompt = "\n".join([
        components["PERSONA"],
        components["HIGH_LEVEL_TASK"],
        components["LOW_LEVEL_TASK"]
    ])

    client = OpenAI()

    try:
        completion = client.beta.chat.completions.parse(
            temperature = 0,
            model = "gpt-4o-2024-08-06",
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": "Let's find the date mentioned based on the prompt."
                }
            ],
            response_format=RouterDate,
        )

        output = completion.choices[0].message.parsed
        parsed_router_date_llm = output.model_dump(mode="yaml")
        print("parsed_router_date_llm: ", parsed_router_date_llm)

        return parsed_router_date_llm
    
    except Exception as e:
        print("Error: ", e)
        pass


def process_router_type_llm(router_name):
    """
    Use the OpenAI API to help us extract the type information.
    
    Parameters:
        router_name:    The router name
    """
    
    prompt_file = "process_router_type_prompt.txt"
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
            temperature = 0,
            # model = "gpt-4o-mini",
            model = "gpt-4o-2024-08-06",
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
            response_format=RouterType,
        )

        output = completion.choices[0].message.parsed
        parsed_router_type_llm = output.model_dump(mode="yaml")
        print("parsed_router_type_llm: ", parsed_router_type_llm)

        return parsed_router_type_llm
    
    except Exception as e:
        print("Error: ", e)
        pass


if __name__ == "__main__":

    result_directory = "../result/Cisco/"
    routers_without_url = "../result/routers_without_url.csv"

    router_names = [name for name in os.listdir(result_directory) if os.path.isdir(os.path.join(result_directory, name))]
    random.seed(42)
    random_selection = random.sample(router_names, 3)

    # for router_name in tqdm(random_selection):
    for router_name in tqdm(random_selection):
        print("\n===================================================================================================================")
        print("\n", router_name, "\n")
        filtered_netbox_file = result_directory + router_name + "/" + router_name + "_filtered_netbox.yaml"
        filtered_netbox_file_content = load_yaml(filtered_netbox_file)
        # This router contains the URL
        if not is_model_without_url(router_name, routers_without_url):
            url = filtered_netbox_file_content["datasheet_url"]
            print("Category 1 -> There is a URL in the netbox yaml -> ", url)
            parsed_router_info_llm = process_datasheet_with_url_llm(router_name, url)
        # This router DOES NOT contain the URL
        else:
            manufacturer = filtered_netbox_file_content["manufacturer"]
            url = find_router_url(router_name, manufacturer)
            # If the url can be found
            if url:
                print("Category 2 -> The URL is found via LLM ->", url)
                data = {"datasheet_url": url}
                filtered_netbox_file_content.update(data)
                save_yaml(filtered_netbox_file_content, filtered_netbox_file)
                parsed_router_info_llm = process_datasheet_with_url_llm(router_name, url)
            else:
                print("Category 3 -> No URL can be found")
                parsed_router_info_llm = process_datasheet_without_url_llm(router_name)
        print("parsed_router_info_llm: ", parsed_router_info_llm)
        
        # Write the info parsed by LLM to a yaml file and store it in the same directory of its associated filtered_network.yaml
        router_result_dirctory = result_directory + router_name + "/"
        router_general_llm_file = router_name + "_general_llm.yaml"
        save_yaml(parsed_router_info_llm, router_result_dirctory+router_general_llm_file)
        
        # Write the date into the yaml
        router_result_dirctory = result_directory + router_name + "/"
        router_date_llm_file = router_name + "_date_llm.yaml"
        parsed_router_date_llm = process_router_date_llm(router_name)
        save_yaml(parsed_router_date_llm, router_result_dirctory+router_date_llm_file)

        # Write the router type into the yaml
        router_result_dirctory = result_directory + router_name + "/"
        router_type_llm_file = router_name + "_type_llm.yaml"
        parsed_router_type_llm = process_router_type_llm(router_name)
        save_yaml(parsed_router_type_llm, router_result_dirctory+router_type_llm_file)
