import os
import requests
import pandas as pd
from googlesearch import search
from bs4 import BeautifulSoup
from tqdm import tqdm
from load_file import *
from extract_data_llm import *
from merge_router_info import *


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



def verify_and_adjust_url(url):
    try:
        # Initiate a head request to check for content type and redirection
        response = requests.head(url, allow_redirects=True)
        
        # Capture the final URL after redirection (if any)
        final_url = response.url
        content_type = response.headers.get('Content-Type', '').lower()
        
        # If the final URL ends with .pdf or the content type is PDF, return the original URL
        if final_url.endswith('.pdf') or 'pdf' in content_type:
            print("The URL points to a PDF.")
            return url
        
        # If redirected to an HTML page (not PDF), adjust the final URL to avoid .pdf inappropriately
        elif final_url.endswith('.html') or 'html' in content_type:
            print("The URL is not a PDF; it's an HTML page.")
            return final_url
        
        # If not PDF and doesn't explicitly end with .html, replace .pdf with .html as a fallback
        else:
            print("The URL is ambiguous; changing to an HTML format as a fallback.")
            return url.replace('.pdf', '.html')
    
    except requests.RequestException as e:
        print(f"Error checking URL: {e}")
        return url


def search_router_url_google(router_name, router_series):
    
    query = f"{router_name} {router_series} datasheet"
    possible_urls = {router_series: {router_name: []}}

    for result in search(query, num_results=5):
        possible_urls[router_series][router_name].append(result)
    
    return possible_urls


def extract_router_general_info(filtered_netbox_file_content, filtered_netbox_file, flag=True):
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
        flag = True
    # This router DOES NOT contain the URL based on the NetBox
    else:
        url = find_router_url_llm(router_series)
        # If the URL can be found and its content is not deprecated
        if url and not is_deprecated_404(url):
            url = verify_and_adjust_url(url)
            print("Category 2 -> The URL is found via LLM ->", url)
            data = {"datasheet_url": url}
            filtered_netbox_file_content.update(data)
            save_yaml(filtered_netbox_file_content, filtered_netbox_file)
            parsed_router_info_llm = extract_datasheet_with_url_llm(router_name, url)
            if url.lower().endswith(".pdf"):
                parsed_router_info_llm["datasheet_pdf"] = url
            flag = True
        # The URL is still missing or the found URL is deprecated
        else:
            print("Category 3 -> No URL can be found")
            # For this part, I think there are two alternatives:
            # 1.    googlesearch-python -> a Python package helping us to search something via Google in python 
            #       -> It will return us the URL
            #       -> Record them in a json
            #       -> Later on, I also found that for the same series, some contain the url while some don't.
            #       -> We can compare our results with those, and then it will increase our confidence to get the correct URL.
            #       -> Manually choose the URL and input it to extract_datasheet_with_url_llm
            # 2.    currently skip this part in order to catch up with the deadline
            # parsed_router_info_llm = extract_datasheet_without_url_llm(router_name)
            parsed_router_info_llm = search_router_url_google(router_name, router_series)
            flag = False

    return parsed_router_info_llm, flag


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

    # Make sure that possible_router_urls_json_file_path is always brand new when the code begins to run
    possible_router_urls_json_file_path = "../category_and_clarification/possible_router_urls.json"
    if os.path.exists(possible_router_urls_json_file_path):
        os.remove(possible_router_urls_json_file_path)
    
    possible_router_urls = {}

    for series_folder in tqdm(os.listdir(result_dir)):

        # All the following code is conducted for the routers under the same series
        print("series_folder: ", series_folder)
        series_path = os.path.join(result_dir, series_folder)

        if series_folder in [\
            "me_3600x_series_ethernet_access_switches", 
            "cisco_business_350_series_managed_switches", \
            "nexus_2000_series_fabric_extenders", \
            "aironet_2700_series_access_points", \
            "cisco_350_series_managed_switches", \
            "aironet_1240_series", \
            "cisco_300_series_managed_switches", \
            "catalyst_2960_plus_series_switches", \
            "500_series_wpan_industrial_routers", \
            "cisco_2500_series_access_servers", \
            "cisco_asa_5500_x_series_firewalls", \
            "catalyst_3650_series_switches", \
            "asa_5500_x_series_next_generation_firewalls", \
            "small_business_rv_series_routers"
        ]:
            continue
                
        for router_name in os.listdir(series_path):

            print("===================================================================================================================")
            print("router_name: ", router_name, "\n")

            filtered_netbox_file = series_path + "/" + router_name + "/filtered_netbox.yaml"
            filtered_netbox_file_content = load_yaml(filtered_netbox_file)

            # Extract the general information based on the URL datasheet
            parsed_router_info_llm, flag = extract_router_general_info(filtered_netbox_file_content, filtered_netbox_file)
            print("parsed_router_info_llm: ", parsed_router_info_llm)
            if flag:
                router_general_llm_file = series_path + "/" + router_name + "/general_llm.yaml"
                save_yaml(parsed_router_info_llm, router_general_llm_file)
            else:
                print("parsed_router_info_llm: ", parsed_router_info_llm)
                possible_router_urls = merge_dicts(possible_router_urls, parsed_router_info_llm)
            
            # Extract the date: 'release date', 'end-of-sale date' and 'end-of-support date'
            router_series = filtered_netbox_file_content["series"]
            router_date_llm_file = series_path + "/" + router_name + "/date_llm.yaml"
            parsed_router_date_llm = extract_router_date_info(router_series)
            print("parsed_router_date_llm: ", parsed_router_date_llm)
            save_yaml(parsed_router_date_llm, router_date_llm_file)

            # Write the router type into the yaml
            router_type_llm_file = series_path + "/" + router_name + "/type_llm.yaml"
            parsed_router_type_llm = process_router_type_llm(router_name)
            print("parsed_router_type_llm: ", parsed_router_type_llm)
            save_yaml(parsed_router_type_llm, router_type_llm_file)

        counter += 1
        
        if counter == 20:
            break

    save_json(possible_router_urls, possible_router_urls_json_file_path)
