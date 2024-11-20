import os
import json
import re
import requests
import subprocess
from tqdm import tqdm
from bs4 import BeautifulSoup
from load_file import *
from merge_router_info import *
from grasp_cisco_router_series import *
from extract_data_llm import *


def is_deprecated_404(url):
    """
    Detect if a given URL is actually a deprecated 404 page or if it's a PDF file.
    
    Parameters:
        url (str): The URL to check.
        
    Returns:
        bool: True if the URL is a 404 or deprecated page, False otherwise.
    """
    try:

        if url == None:
            return True

        response = requests.get(url, timeout=10, allow_redirects=True)
        
        # Check if response code is 404
        if response.status_code == 404:
            return True

        # Check if the content type is PDF
        content_type = response.headers.get("Content-Type", "").lower()
        if "pdf" in content_type:
            return False

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for '404' in the title or meta tags
        title = soup.title.string if soup.title else ""
        meta_404 = soup.find("meta", {"name": "robots", "content": "noindex"})

        if "404" in title.lower() or meta_404:
            return True

    except requests.RequestException as e:
        # If there's an error with the request itself, treat as 404
        print(f"Error accessing URL {url}: {e}")
        return True

    return False


def grasp_url_netbox(content):
    """
    Grasp the URL from the netbox if it exists

    Parameter:
        content:    The content of the netbox yaml file
    
    Returns:
        The URL datasheet of a router datasheet if it exists,
        otherwise return None
    """
    url = content.get("comments")
    url_pattern = re.compile(r'https?://[^\s\)]+')
    url_match = url_pattern.search(str(url))

    if url_match:
        url = url_match.group()
        if url.endswith("htmlhtml"):
            url = url[:-4]
        return url
    else:
        return None


def filter_netbox_info(psu_category, content, url):
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
    output_dict["datasheet_url"] = url

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

    """
    For the NetBox dataset, here are three categories defined by ourselves:
    ---------------------------------------------------------------------------
    | Category 1 | url already available in the NetBox                        |
    |-------------------------------------------------------------------------|
    | Category 2 | url NOT available in the NetBox but can be found online    |
    |-------------------------------------------------------------------------|
    | Category 3 | url NOT available in the NetBox AND CANNOT be found online |
    ---------------------------------------------------------------------------
    """
    psu_category = "../category_and_clarification/psu_category.json" # This file is manually created
    dataset_dir = "../dataset/"
    result_dir = "../result"

    for manufacturer in tqdm(os.listdir(dataset_dir)):

        print("manufacturer: ", manufacturer)

        dataset_manufacturer_path = os.path.join(dataset_dir, manufacturer)
        manufacturer = manufacturer.lower()
        result_manufacturer_path = os.path.join(result_dir, manufacturer)
        os.makedirs(result_manufacturer_path, exist_ok=True)
        valid_router_url = {"router":[], "url": []}

        for router in tqdm(os.listdir(dataset_manufacturer_path)):
            
            content = load_yaml(os.path.join(dataset_manufacturer_path, router))

            router_name = content["model"]

            url = grasp_url_netbox(content)
            url = None if is_deprecated_404(url) else url

            """
            The result path may depend as there is one more directory for Cisco series
            For Cisco, it shall be 'result/cisco/<router_series>/<router_name>/filtered_netbox.yaml'
            For Arista/Juniper, it shall be 'result/<manufacturer>/<router_name>/filtered_netbox.yaml'
            """
            router_name_str = str(router_name).lower().replace("-", "_").replace(" ", "_").strip()
            filter_netbox_yaml_file = "filtered_netbox.yaml"
            if manufacturer == "cisco":
                command = ['find', '../result/', '-type', 'd', '-iname', router_name_str]
                result_router_dir = subprocess.run(command, check=True, stdout=subprocess.PIPE, text=True).stdout.strip()
            else:
                result_router_dir = os.path.join(result_manufacturer_path, router_name_str)
            os.makedirs(result_router_dir, exist_ok=True)

            # Category 1
            if url:
                valid_router_url["router"].append(router)
                valid_router_url["url"].append(url)
                filtered_content = filter_netbox_info(psu_category, content, url)
                save_yaml(filtered_content, os.path.join(result_router_dir, filter_netbox_yaml_file))
            
            # Category 2 and 3
            else:
                url = find_router_url_llm(router_name)
                # Category 2
                if url and not is_deprecated_404(url):
                    filtered_content = filter_netbox_info(psu_category, content, url)
                    filtered_content["datasheet_url"] = str(url)
                    save_yaml(filtered_content, os.path.join(result_router_dir, filter_netbox_yaml_file))
                # Category 3 is not needed right now
                
        # After iterating all the Category 1 router, store the valid url into a csv file
        router_df = pd.DataFrame(valid_router_url)
        valid_url_csv_file = os.path.join(result_manufacturer_path, "valid_router_urls.csv")
        router_df.to_csv(valid_url_csv_file, index=False)
