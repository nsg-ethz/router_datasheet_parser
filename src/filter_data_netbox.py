import os
import json
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from typing import Optional
from pydantic import BaseModel, Field
from load_file import *
from merge_router_info import *


def extract_supported_products_series(url):
    """
    Extract the Cisco routers series information.

    Parameters:
        url:    The URL of the Cisco routers series.
    
    Returns:
        A dict data-type variable with the key of series name, and the value of series webpage.
    """
    html_content = requests.get(url).text
    soup = BeautifulSoup(html_content, 'html.parser')
    all_supported_products = soup.find('div', {'id': 'allSupportedProducts'})
    routers_data = {}

    # Find all router number sections (0-9 and specific models under it)
    for item in all_supported_products.find_all('li'):
        number_tag = item.find('span', class_='number')
        if number_tag:
            number = number_tag.text.strip()
            router_dict = {}
            
            # Find all the associated router names and links
            for data_item in item.find_all('span', class_='data-items'):
                router_name = data_item.text.strip()
                link_tag = data_item.find('a', class_='link-url')
                if link_tag and router_name:
                    router_dict[router_name] = link_tag['href']

            routers_data[number] = router_dict

    return routers_data


class RouterSeries(BaseModel):
    router_series: Optional[str] = Field(description="The router series which this router model belong to.")


def find_router_series(cisco_router_series_file_path, router_name, manufacturer=None):
    """
    Find the corresponding router series with the help of LLM.

    Parameters:
        cisco_router_series_file_path:   The file path indicating the Cisco router series information.
        router_name:                     The name of the router.
        manufacturer:                    The manufacturer of a router, e.g., Cisco.

    Returns:
        The series of the router.                            
    """
    client = OpenAI()
    system_prompt = f"Given the router model '{router_name}', its associated manufacturer '{manufacturer}' and the '{cisco_router_series_file_path}' file\
                    please return the router series for this specific model. \
                    It will be perfect if the router series belongs to one of the those in '{cisco_router_series_file_path}'. \
                    If you can't find the corresponding series in '{cisco_router_series_file_path}', then use your own knowledge to search for the series. \
                    If you still can't find it, leave it empty. \
                    For example, router 'Catalyst 3650-48FQM-L' belongs to the series 'Catalyst 3650 Series Switches'"

    cisco_router_series = load_json(cisco_router_series_file_path)
    cisco_router_series_str = json.dumps(cisco_router_series)

    completion = client.beta.chat.completions.parse(
        temperature = 0,
        model = "gpt-4o",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": cisco_router_series_str
            }
        ],
        response_format=RouterSeries,
    )

    output_series = completion.choices[0].message.parsed.router_series

    return output_series


def filter_netbox_info(psu_category, content, routers_without_url):
    """
    Write all the necessary information which can be extracted from the original
    netbox yaml file. Specifically speaking, they are:
        -   manufacturer
        -   model
        -   slug
        -   part_number
        -   u_height
        -   url (if it exists, otherwise log it in routers_without_url.csv)
        -   psu:
            -   number_of_modules
            -   power_rating (maximum_draw)
            -   part_numbe (type)
    
    Parameters:
        psu_category:   a json file which was created in count_netbox_keys
                        to judge if a power-ports or module-bays is a psu
                        module or not.
        router_dir:     A router dictory storing all the netbox router info
    
    Returns:
        A yaml file with the name format <router_model>_filtered_netbox.yaml
        containing the information mentioned above.
    """
    # Load .json for the psu category
    with open(psu_category, "r") as json_file:
        data = json.load(json_file)
        psu_list = data["psu"]

    # Get prepared for writing this router info
    output_dict = {}
    output_dict["manufacturer"] = content.get("manufacturer", output_dict.get("manufacturer"))
    output_dict["model"] = content.get("model", output_dict.get("model"))
    output_dict["slug"] = content.get("slug", output_dict.get("slug"))
    output_dict["part_number"] = content.get("part_number", output_dict.get("part_number"))
    output_dict["u_height"] = content.get("u_height", output_dict.get("u_height"))

    # Log the model name in the CSV if "url is missing"
    url = content.get("comments")
    url_pattern = re.compile(r'https?://[^\s\)]+')
    url_match = url_pattern.search(str(url))
    if url_match:
        url = url_match.group()
        output_dict["datasheet_url"] = url
    else:
        output_dict["datasheet_url"] = None
        record_without_url_csv(routers_without_url, output_dict["manufacturer"], output_dict["model"])

    """
    psu related:
    1. efficiency_rating -> [Bronze, Silver, Gold, Platinum, Titanium] -> LLM
    2. power_rating -> maximum_draw -> netbox
    3. numbers_of_modules -> netbox
    4. part_number -> netbox
    """
    output_dict["psu"] = {"number_of_modules": 0, "efficiency_rating": None, "power_rating": None, "part_number": None}

    # Iterate over potential power sources if they exist
    for key in ["power-ports", "module-bays"]:
        if content.get(key):
            for module in content[key]:
                if module["name"] in psu_list:
                    output_dict["psu"]["number_of_modules"] += 1
                    output_dict["psu"]["power_rating"] = module.get("maximum_draw", None)
                    output_dict["psu"]["part_number"] = module.get("type", None)
            # Exit after processing "power-ports" if found
            break
    
    return output_dict


if __name__ == "__main__":

    dataset_dir = "../dataset/Cisco/"

    # Generate the 'router_switch_series.json' file
    cisco_router_url = "https://www.cisco.com/c/en/us/support/routers/index.html"
    cisco_switch_url = "https://www.cisco.com/c/en/us/support/switches/index.html"
    cisco_wireless_url = "https://www.cisco.com/c/en/us/support/wireless/index.html"

    cisco_routers_data = extract_supported_products_series(cisco_router_url)
    cisco_switches_data = extract_supported_products_series(cisco_switch_url)
    cisco_wireless_data = extract_supported_products_series(cisco_wireless_url)

    merged_data = {}
    merged_data = merge_dicts(merged_data, cisco_routers_data)
    merged_data = merge_dicts(merged_data, cisco_switches_data)
    merged_data = merge_dicts(merged_data, cisco_wireless_data)
    cisco_router_series_file_path = "../category_and_clarification/router_switch_series.json"
    save_json(merged_data, cisco_router_series_file_path)

    psu_category = "../category_and_clarification/psu_category.json" # This file is manually created
    os.makedirs("../result/", exist_ok=True)
    routers_without_url = "../result/routers_without_url.csv"

    # Delete the file if it already exists to ensure a fresh start
    # And write header to create new CSV file with header at the begining
    if os.path.exists(routers_without_url):
        os.remove(routers_without_url)
    record_without_url_csv(routers_without_url, "manufacturer", "model", write_header=True)

    files = sorted([f for f in os.listdir(dataset_dir) if os.path.isfile(os.path.join(dataset_dir, f))])

    for filename in tqdm(files):
        print("filename: ", filename)
        content = load_yaml(os.path.join(dataset_dir, filename))
        router_name = content["model"]
        manufacturer = content["manufacturer"]
        
        router_series = find_router_series(cisco_router_series_file_path, router_name, manufacturer)
        print("router_series: ", router_series)
        router_series_str = str(router_series).lower().replace("-", "_").replace(" ", "_").strip()
        result_series_dir = "../result/" + str(manufacturer).lower() + "/" + str(router_series_str)
        os.makedirs(result_series_dir, exist_ok=True)
        
        filtered_content = filter_netbox_info(psu_category, content, routers_without_url)
        filtered_content["series"] = str(router_series)
        filter_netbox_yaml_file = "filtered_netbox.yaml"

        # Save the result into the appointed folder
        result_router_dir = result_series_dir + "/" + str(router_name).lower().replace("-", "_").replace(" ", "_").strip()
        os.makedirs(result_router_dir, exist_ok=True)
        save_yaml(filtered_content, result_router_dir + "/" + filter_netbox_yaml_file)
