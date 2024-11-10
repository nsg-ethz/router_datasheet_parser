import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm
from load_file import *
from extract_data_llm import *


def is_model_without_url(router_name, routers_without_url_csv):
    """
    Judge if this router contains a URL

    Parameters:
        router_name:                The router model name
        routers_without_url_csv:    The csv file containing the info of routers without URL
    
    Returns:
        A boolean value, true if this router does not contain URL, false otherwise
    """
    df = pd.read_csv(routers_without_url_csv)
    return router_name in df["model"].values


def is_deprecated_404(url):
    """
    Detect if a given URL is actually a deprecated 404 page.
    
    Parameters:
        url (str): The URL to check.
        
    Returns:
        bool: True if the URL is a 404 or deprecated page, False otherwise.
    """
    try:
        response = requests.get(url)
        
        # Check if response code is 404
        if response.status_code == 404:
            return True

        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for '404' in the title or meta tags
        title = soup.title.string if soup.title else ""
        meta_404 = soup.find("meta", {"name": "robots", "content": "noindex"})

        if "404" in title.lower() or meta_404:
            return True
        
    except requests.RequestException as e:
        # If there's an error with the request itself, treat as 404 (depends on your needs)
        print(f"Error accessing URL {url}: {e}")
        return True

    return False


def extract_router_general_info(filtered_netbox_file_content, filtered_netbox_file):
    """
    Extract the general info of a given router

    Parameters:
        filtered_netbox_file_content: The filtered netbox router info
    
    Returns:
        The extracted information.
    """
    routers_without_url_file_path = "../result/routers_without_url.csv"
    router_name = filtered_netbox_file_content["model"]
    router_series = filtered_netbox_file_content["series"]

    # This router contains the URL
    if not is_model_without_url(router_name, routers_without_url_file_path):
        url = filtered_netbox_file_content["datasheet_url"]
        print("Category 1 -> There is a URL in the netbox yaml -> ", url)
        parsed_router_info_llm = extract_datasheet_with_url_llm(router_name, url)
    
    # This router DOES NOT contain the URL based on the NetBox
    else:
        url = find_router_url_llm(router_series)
        # If the URL can be found and its content is not deprecated
        if url and not is_deprecated_404(url):
            print("Category 2 -> The URL is found via LLM ->", url)
            data = {"datasheet_url": url}
            filtered_netbox_file_content.update(data)
            save_yaml(filtered_netbox_file_content, filtered_netbox_file)
            parsed_router_info_llm = extract_datasheet_with_url_llm(router_name, url)
        # The URL is still missing or the found URL is deprecated
        else:
            print("Category 3 -> No URL can be found")
            parsed_router_info_llm = extract_datasheet_without_url_llm(router_name)

    return parsed_router_info_llm


def find_date_url_by_series(router_series):

    print("router_series: ", router_series)
    router_series_json_file_path = "../category_and_clarification/router_series.json"
    router_series_json_file_content = load_json(router_series_json_file_path)

    for key, val in router_series_json_file_content.items():
        if isinstance(val, dict):
            for series_name, url in val.items():
                if (router_series.lower() in series_name.lower()) or (series_name.lower() in router_series.lower()):
                    return url
        elif (router_series.lower() in key.lower()) or (key.lower() in router_series.lower()):
            return val
    
    # If not found, return None
    return None


def extract_router_date_info(router_series):

    router_date_series_url = find_date_url_by_series(router_series)
    parsed_router_date_llm = process_router_date_llm(router_series, router_date_series_url)
        
    return parsed_router_date_llm


if __name__ == "__main__":

    # Currently, the code is only for Cisco
    result_dir = "../result/cisco/"
    counter = 0 # This is only used for testing the info accuracies

    for series_folder in tqdm(os.listdir(result_dir)):

        print("series_folder: ", series_folder)
        series_path = os.path.join(result_dir, series_folder)
        if series_folder == "me_3600x_series_ethernet_access_switches":
            continue
        
        for router_name in os.listdir(series_path):

            print("\n")
            print("===================================================================================================================")
            print("router_name: ", router_name, "\n")

            filtered_netbox_file = series_path + "/" + router_name + "/filtered_netbox.yaml"
            filtered_netbox_file_content = load_yaml(filtered_netbox_file)

            # Extract the general information based on the URL datasheet
            parsed_router_info_llm = extract_router_general_info(filtered_netbox_file_content, filtered_netbox_file)
            print("parsed_router_info_llm: ", parsed_router_info_llm)
            # router_general_llm_file = series_path + "/" + router_name + "/general_llm.yaml"
            # save_yaml(parsed_router_info_llm, router_general_llm_file)
            
            # Extract the date: 'release date', 'end-of-sale date' and 'end-of-support date'
            router_series = filtered_netbox_file_content["series"]
            router_date_llm_file = series_path + "/" + router_name + "/date_llm.yaml"
            parsed_router_date_llm = extract_router_date_info(router_series)
            print("parsed_router_date_llm: ", parsed_router_date_llm)
            # save_yaml(parsed_router_date_llm, router_date_llm_file)

            # Write the router type into the yaml
            router_type_llm_file = series_path + "/" + router_name + "/type_llm.yaml"
            parsed_router_type_llm = process_router_type_llm(router_name)
            print("parsed_router_type_llm: ", parsed_router_type_llm)
            # save_yaml(parsed_router_type_llm, router_type_llm_file)

        counter += 1
        
        if counter == 3:
            break
