import os
import json
import re
import requests
from bs4 import BeautifulSoup
from load_file import *
from merge_router_info import *
from grasp_router_series import *
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


def extract_supported_products_series(manufacturer, url):
    """
    Extract the Cisco routers series information.

    Parameters:
        url:    The URL of the Cisco routers series.
    
    Returns:
        A dict data-type variable with the key of series name, and the value of series webpage.
    """
    if manufacturer.lower() == "Cisco":
        html_content = requests.get(url).text
        soup = BeautifulSoup(html_content, 'html.parser')
        all_supported_products = soup.find('div', {'id': 'allSupportedProducts'})
        products_data = {}

        # Extract series information from the 0-9 section
        for item in all_supported_products.find_all('li'):
            number_tag = item.find('span', class_='number')
            if number_tag:
                number = number_tag.text.strip()
                series_dict = {}

                # Find all the associated series names and links in the 0-9 section
                for data_item in item.find_all('span', class_='data-items'):
                    series_name = data_item.text.strip()
                    link_tag = data_item.find('a', class_='link-url')
                    if link_tag and series_name:
                        series_dict[series_name] = "https://www.cisco.com" + link_tag['href']
                products_data[number] = series_dict

        # Extract series information from the A-Z section
        az_section = all_supported_products.find('ul', {'id': 'prodByAlpha'})
        if az_section:
            for az_item in az_section.find_all('li'):
                link_tag = az_item.find('a')
                if link_tag:
                    series_name = link_tag.text.strip()
                    series_link = link_tag['href']
                    products_data[series_name] = "https://www.cisco.com" + series_link

    return products_data


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
    # record_without_url_csv(routers_without_url, output_dict["manufacturer"], output_dict["model"])

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

        if manufacturer == "cisco":

            cisco_router_series_file_path = os.path.join(result_manufacturer_path, "router_series.json")

            valid_router_url = {"router":[], "url": []}

            for router in tqdm(os.listdir(dataset_manufacturer_path)):
                
                content = load_yaml(os.path.join(dataset_manufacturer_path, router))

                router_name = content["model"]

                # load the valid router URL -> At present, we only care about Category 1
                url = grasp_url_netbox(content)
                url = None if is_deprecated_404(url) else url

                if url:

                    print("router we care about: ", router_name)

                    valid_router_url["router"].append(router)
                    valid_router_url["url"].append(url)
                
                    router_series = find_router_series(cisco_router_series_file_path, router_name, manufacturer)
                    print("router_series: ", router_series)
                    router_series_str = str(router_series).lower().replace("-", "_").replace(" ", "_").strip()
                    result_series_dir = os.path.join(result_manufacturer_path, router_series_str)
                    os.makedirs(result_series_dir, exist_ok=True)
                    
                    filtered_content = filter_netbox_info(psu_category, content, url)
                    filtered_content["series"] = str(router_series)
                    filter_netbox_yaml_file = "filtered_netbox.yaml"

                    # Save the result into the 'result/<router_series>/<router_name>/filtered_netbox.yaml'
                    result_router_dir = os.path.join(result_series_dir, str(router_name).lower().replace("-", "_").replace(" ", "_").strip())
                    os.makedirs(result_router_dir, exist_ok=True)
                    save_yaml(filtered_content, os.path.join(result_router_dir, filter_netbox_yaml_file))
            
            # After iterating all the Category 1 router, store the valid url into a csv file
            router_df = pd.DataFrame(valid_router_url)
            valid_url_csv_file = os.path.join(result_manufacturer_path, "valid_router_urls.csv")
            router_df.to_csv(valid_url_csv_file, index=False)
            break
