import os
import requests
from googlesearch import search
from bs4 import BeautifulSoup
from datetime import datetime
from load_file import *
from filter_data_netbox import *
from extract_data_llm import *
from merge_router_info import *
from process_general_info_date_type import *


def find_router_series_url(series_path):
    """
    THIS FUNCTION IS CURRENTLY NOT USED!!!
    The intention is to collect all existing URLs for a given router series.
    Normally, routers from the same series may share a URL.
    This function is implemented to faciliate to locate URL for routers
    without URL datasheet in NetBox.

    Parameters:
        series_path:    The path for a given router series.
    
    Returns:
        Existing URLs for this series.
    """

    existing_router_urls = []

    for router_name in os.listdir(series_path):

        filtered_netbox_file = os.path.join(series_path, router_name, "filtered_netbox.yaml")
        filtered_netbox_file_content = load_yaml(filtered_netbox_file)
        if filtered_netbox_file_content["datasheet_url"]:
            existing_router_urls.append(filtered_netbox_file_content["datasheet_url"])

    return list(set(existing_router_urls))


def search_router_url_google(router_name, router_series):
    """
    THIS FUNCTION IS CURRENTLY NOT USED!!!
    This function is mainly designed for Category 3.
    The intention is to directly call Google to return the top 5
    search results of a given router. Just like directly input
    router name into Google and find the top 5 most relevant
    URL datasheet of this router.

    Parameters:
        router_name:    A router model name.
        router_series:  A router series.
    
    Returns:
        Top 5 most-likely router url datasheet.
    """

    query = f"{router_name} {router_series} datasheet"
    possible_urls = {router_series: {router_name: []}}

    for result in search(query, num_results=5):
        possible_urls[router_series][router_name].append(result)
    
    return possible_urls


def verify_and_adjust_url(url):
    """
    Verify if a url is still reachable and valid.
    The URL stored in NetBox or grasped by LLM may
    be reachable but are deprecated. This function
    also tries to adjust the url into a correct format.

    Parameters:
        url:    A webpage.
    
    Returns:
        A verified url.
    """
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


def extract_router_general_info(filtered_netbox_file_content):
    """
    Extract the general info of a given router.
    Attention, this function is waiting to be extended for Category 3.

    Parameters:
        filtered_netbox_file_content: The filtered netbox router info.
    
    Returns:
        The extracted information.
    """
    router_name = filtered_netbox_file_content["model"]

    url = filtered_netbox_file_content["datasheet_url"]
    parsed_router_info_llm = extract_datasheet_with_url_llm(router_name, url)

    return parsed_router_info_llm


def find_date_url_by_series(manufacturer, router_series):
    """
    Currently, only Cisco routers will use this function.
    Based on 'router_series.json', it will return the URL where key dates can be found.

    Parameters:
        manufacturer:   The manufacturer of a router, e.g., Cisco.
        router_series:  The series of a router.
    
    Returns:
        The URL storing the key dates from router_series.json
    """
    router_series_json_file_path = os.path.join("../result/", manufacturer, "router_series.json")
    router_series_json_file_content = load_json(router_series_json_file_path)

    for key, val in router_series_json_file_content.items():
        if isinstance(val, dict):
            for series_name, url in val.items():
                if (router_series.lower() in series_name.lower()) or (series_name.lower() in router_series.lower()):
                    return url
        elif (router_series.lower() in key.lower()) or (key.lower() in router_series.lower()):
            return val

    return None


def process_router_date_cisco_support(router_date_series_url):
    """
    Currently, This function is tailored to Cisco rotuers.
    Based on the EOL url stored in router_series.json, it will
    find the release_date, end_of_sale_date, and end_of_support_date
    if they exist.

    Parameters:
        router_date_series_url: The url showing the EOL of the router.
    
    Returns:
        The release_date, end_of_sale_date, and end_of_support_date
        if they exist.
    """
    try:
        response = requests.get(router_date_series_url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')

        date_labels = {
            "Series Release Date": ["Series Release Date", "Release Date"],
            "End-of-Sale Date": ["End-of-Sale Date"],
            "End-of-Support Date": ["End-of-Support Date"]
        }

        extracted_dates = {}

        table = soup.find("table", class_="birth-cert-table")
        
        if table:
            rows = table.find_all("tr")
            for row in rows:
                label_cell = row.find("th")
                date_cell = row.find("td")
                
                if label_cell and date_cell:
                    label = label_cell.get_text(strip=True)
                    date_text = date_cell.get_text(strip=True)

                    # Check each date label key for matching alternative labels
                    for main_label, alternatives in date_labels.items():
                        if label in alternatives:
                            try:
                                # Parse date to ISO 8601 format
                                parsed_date = datetime.strptime(date_text, '%d-%b-%Y').date().isoformat()
                                extracted_dates[main_label] = parsed_date
                            except ValueError:
                                print(f"Could not parse date for {label}. Original text: {date_text}")
        
        return extracted_dates

    except requests.RequestException as e:
        print(f"Error accessing URL {router_date_series_url}: {e}")
        return None


def extract_router_date_info(manufacturer, router_series):
    """
    Extract the router date.

    Parameters:
        manufacturer:   The manufacturer of a router.
        router_series:  The series of a router.
    
    Returns:
        The parsed router date including release_date, 
        end_of_sale_date, and end_of_support_date.
    """
    router_date_series_url = find_date_url_by_series(manufacturer, router_series)
    if router_date_series_url and manufacturer.lower() == "cisco":
        print("router_date_series_url: ", router_date_series_url)
        parsed_router_date = process_router_date_cisco_support(router_date_series_url)
        return parsed_router_date
    else:
        # parsed_router_date_llm = process_router_date_llm(router_series, router_date_series_url)
        return None


if __name__ == "__main__":

    dataset_dir = "../dataset/"
    result_dir = "../result"

    for manufacturer in os.listdir(result_dir):

        print("manufacturer: ", manufacturer)

        manufacturer = manufacturer.lower()
        manufacturer_dir = os.path.join(result_dir, manufacturer)

        # For Cisco, there is one more directory for series
        if manufacturer == "cisco":

            for series_dir in os.listdir(manufacturer_dir):
                series_folder = os.path.join(manufacturer_dir, series_dir)
                for root, dirs, files in os.walk(series_folder):
                    for router_dir in dirs:
                        filtered_netbox_file = os.path.join(series_folder, router_dir, "filtered_netbox.yaml")
                        if not os.path.isfile(filtered_netbox_file):
                            continue
                        filtered_netbox_file_content = load_yaml(filtered_netbox_file)

                        # Part 1: Extract the general information based on the URL datasheet
                        parsed_router_info_llm = extract_router_general_info(filtered_netbox_file_content)
                        router_general_llm_file = os.path.join(series_folder, router_dir, "general_llm.yaml")
                        save_yaml(parsed_router_info_llm, router_general_llm_file)

                        # Part 2: Extract the date: 'release date', 'end-of-sale date' and 'end-of-support date'
                        # For Cisco, LLM is not needed. Beautiful Soup can be used to reduce the cost
                        router_date = {
                            "release_date": None,
                            "end_of_sale": None,
                            "end_of_support": None
                        }
                        series_file = os.path.join(series_folder, router_dir, "series.yaml")
                        series_file_content = load_yaml(series_file)
                        router_series = series_file_content["series"]
                        if router_series.lower().startswith(manufacturer.lower()):
                            router_series = router_series[len(manufacturer):].strip()
                        router_date_file = os.path.join(series_folder, router_dir, "date_llm.yaml")
                        parsed_router_date = extract_router_date_info(manufacturer, router_series)
                        if parsed_router_date:
                            router_date["release_date"] = parsed_router_date.get("Series Release Date")
                            router_date["end_of_sale"] = parsed_router_date.get("End-of-Sale Date")
                            router_date["end_of_support"] = parsed_router_date.get("End-of-Support Date")
                        save_yaml(router_date, router_date_file)

                    # Part 3: Extract the router type -> Currently NO need
                    # router_type_llm_file = os.path.join(series_folder, router_dir, "type_llm.yaml")
                    # parsed_router_type_llm = process_router_type_llm(filtered_netbox_file_content["model"])
                    # save_yaml(parsed_router_type_llm, router_type_llm_file)
        
        # For Arista and Juniper, there are no series
        else:

            for root, dirs, files in os.walk(manufacturer_dir):

                for router_dir in dirs:
                    
                    filtered_netbox_file = os.path.join(manufacturer_dir, router_dir, "filtered_netbox.yaml")
                    if not os.path.isfile(filtered_netbox_file):
                        continue
                    filtered_netbox_file_content = load_yaml(filtered_netbox_file)

                    # Part 1: Extract the general information based on the URL datasheet
                    parsed_router_info_llm = extract_router_general_info(filtered_netbox_file_content)
                    router_general_llm_file = os.path.join(manufacturer_dir, router_dir, "general_llm.yaml")
                    save_yaml(parsed_router_info_llm, router_general_llm_file)
                
                    # Part 2: Extract the date: 'release date', 'end-of-sale date' and 'end-of-support date'
                    # Currently, part 2 is not needed for Arista or Juniper
                    # router_date = {
                    #     "release_date": None,
                    #     "end_of_sale": None,
                    #     "end_of_support": None
                    # }
                    # router_series = filtered_netbox_file_content["series"]
                    # if router_series.lower().startswith(manufacturer.lower()):
                    #     router_series = router_series[len(manufacturer):].strip()
                    # router_date_file = os.path.join(series_folder, router_dir, "date_llm.yaml")
                    # parsed_router_date = extract_router_date_info(manufacturer, router_series)
                    # if parsed_router_date:
                    #     router_date["release_date"] = parsed_router_date.get("Series Release Date")
                    #     router_date["end_of_sale"] = parsed_router_date.get("End-of-Sale Date")
                    #     router_date["end_of_support"] = parsed_router_date.get("End-of-Support Date")
                    # print("router_date: ", router_date)
                    # save_yaml(router_date, router_date_file)

                    # Part 3: Extract the router type -> Currently NO need
                    # router_type_llm_file = os.path.join(manufacturer_dir, router_dir, "type_llm.yaml")
                    # parsed_router_type_llm = process_router_type_llm(filtered_netbox_file_content["model"])
                    # save_yaml(parsed_router_type_llm, router_type_llm_file)
