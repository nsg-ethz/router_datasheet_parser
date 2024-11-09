import os
import requests
import pandas as pd
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


def extract_router_general_info(filtered_netbox_file_content):
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
        manufacturer = filtered_netbox_file_content["manufacturer"]
        url = find_router_url_llm(router_name, manufacturer)
        # If the URL can be found
        if url:
            print("Category 2 -> The URL is found via LLM ->", url)
            data = {"datasheet_url": url}
            filtered_netbox_file_content.update(data)
            save_yaml(filtered_netbox_file_content, filtered_netbox_file)
            parsed_router_info_llm = extract_datasheet_with_url_llm(router_name, url)
        # The URL is still missing
        else:
            print("Category 3 -> No URL can be found")
            parsed_router_info_llm = extract_datasheet_without_url_llm(router_name)
    
    return parsed_router_info_llm


if __name__ == "__main__":

    # Currently, the code is only for Cisco
    result_dir = "../result/cisco/"

    for series_folder in tqdm(os.listdir(result_dir)):
        
        print("series_folder: ", series_folder)
        series_path = os.path.join(result_dir, series_folder)
        
        for router_name in os.listdir(series_path):

            print("\n")
            print("===================================================================================================================")
            print("router_name: ", router_name, "\n")

            filtered_netbox_file = series_path + "/" + router_name + "/filtered_netbox.yaml"
            filtered_netbox_file_content = load_yaml(filtered_netbox_file)
            parsed_router_info_llm = extract_router_general_info(filtered_netbox_file_content)
            print("parsed_router_info_llm: ", parsed_router_info_llm)
            
            # Write the info parsed by LLM to a yaml file and store it in the same directory of its associated filtered_network.yaml
            # router_general_llm_file = series_path + "/" + router_name + "/general_llm.yaml"
            # save_yaml(parsed_router_info_llm, router_general_llm_file)
            
            # # Write the date into the yaml
            # router_date_llm_file = series_path + "/" + router_name + "/date_llm.yaml"
            # router_series = filtered_netbox_file_content["series"]
            # parsed_router_date_llm = process_router_date_llm(router_name, router_series)
            # print("parsed_router_date_llm: ", parsed_router_date_llm)
            # # save_yaml(parsed_router_date_llm, router_date_llm_file)

            # # Write the router type into the yaml
            # router_type_llm_file = series_path + "/" + router_name + "/type_llm.yaml"
            # parsed_router_type_llm = process_router_type_llm(router_name)
            # print("parsed_router_type_llm: ", parsed_router_type_llm)
            # # save_yaml(parsed_router_type_llm, router_type_llm_file)
        
        break
