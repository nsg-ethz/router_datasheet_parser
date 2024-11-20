import os
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from load_file import *
from merge_router_info import *
from extract_data_llm import *


def grasp_cisco_supported_products_series(url):
    """
    Extract the Cisco routers series information.

    Parameters:
        url:            The URL of the Cisco routers series.
    
    Returns:
        A dict data-type variable with the key of series name, and the value of series webpage.
    """

    products_data = {}
        
    html_content = requests.get(url).text
    soup = BeautifulSoup(html_content, 'html.parser')
    all_supported_products = soup.find('div', {'id': 'allSupportedProducts'})

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



if __name__ == "__main__":

    dataset_dir = "../dataset/"
    result_dir = "../result"
    manufacturer = "cisco"

    cisco_router_url = "https://www.cisco.com/c/en/us/support/routers/index.html"
    cisco_switch_url = "https://www.cisco.com/c/en/us/support/switches/index.html"
    cisco_wireless_url = "https://www.cisco.com/c/en/us/support/wireless/index.html"

    cisco_routers_data = grasp_cisco_supported_products_series(cisco_router_url)
    cisco_switches_data = grasp_cisco_supported_products_series(cisco_switch_url)
    cisco_wireless_data = grasp_cisco_supported_products_series(cisco_wireless_url)

    merged_data = {}
    merged_data = merge_dicts(merged_data, cisco_routers_data)
    merged_data = merge_dicts(merged_data, cisco_switches_data)
    merged_data = merge_dicts(merged_data, cisco_wireless_data)

    result_manufacturer_dir = os.path.join(result_dir, manufacturer)
    os.makedirs(result_manufacturer_dir, exist_ok=True)
    cisco_router_series_file_path = os.path.join(result_manufacturer_dir, "router_series.json")
    save_json(merged_data, cisco_router_series_file_path)
    print(f"The {manufacturer} series json file has been stored to {cisco_router_series_file_path}")

    # Create the series yaml for Cisco routers
    dataset_manufacturer_path = os.path.join(dataset_dir, "Cisco")
    for router in tqdm(os.listdir(dataset_manufacturer_path)):

        content = load_yaml(os.path.join(dataset_manufacturer_path, router))
        router_name = content["model"]

        # Find the router series and create the associated path
        router_series = find_router_series_llm(cisco_router_series_file_path, router_name, manufacturer)
        print("router_series: ", router_series)
        router_series_str = str(router_series).lower().replace("-", "_").replace(" ", "_").strip()
        result_series_dir = os.path.join(result_manufacturer_dir, router_series_str)
        os.makedirs(result_series_dir, exist_ok=True)

        # Create the router path and store the series result into series.yaml
        result_router_dir = os.path.join(result_series_dir, str(router_name).lower().replace("-", "_").replace(" ", "_").strip())
        os.makedirs(result_router_dir, exist_ok=True)
        save_yaml({"series": router_series}, os.path.join(result_router_dir, "series.yaml"))
