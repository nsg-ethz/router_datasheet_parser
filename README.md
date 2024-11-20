# NetBox Dataset Arista, Cisco and Juniper Parsing

This repository will parse the dataset of Arista, Cisco and Juniper routers from the opensource [NetBox Device Type Library](https://github.com/netbox-community/devicetype-library/tree/master). 

## Environment and Prerequisites
- IDE: Visual Studio Code
- Python: 3.10.12
- Python packages: [requirements.txt](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping)

## Repo Stucture
```
.
├── category_and_clarification
│   ├── psu_category.json
│   └── router_category_clarification.json
├── dataset
├── fig
├── llm_prompt
│   ├── process_datasheet_with_url_prompt.txt
│   ├── process_datasheet_without_url_prompt.txt (not used in this project)
│   ├── process_router_date_prompt.txt
│   └── process_router_type_prompt.txt (not used in this project)
├── markdown
├── result
│   ├── arista
│   │   ├── netbox_keys.yaml
│   │   ├── valid_router_urls.csv
│   │   └── <router_name>
│   │       ├── filtered_netbox.yaml
│   │       ├── general.yaml
│   │       └── merged.yaml
│   ├── cisco
│   │   ├── netbox_keys.yaml
│   │   ├── valid_router_urls.csv
│   │   └── <series_name>
│   │       └── <router_name>
│   │           ├── filtered_netbox.yaml
│   │           ├── general.yaml
│   │           ├── series.yaml
│   │           └── merged.yaml
│   └── juniper
│       ├── netbox_keys.yaml
│       ├── valid_router_urls.csv
│       └── <router_name>
│           ├── filtered_netbox.yaml
│           ├── general.yaml
│           └── merged.yaml
├── src
│   ├── collect_kv_netbox.py
│   ├── extract_data_llm.py
│   ├── filter_data_netbox.py
│   ├── grasp_cisco_router_series.py
│   ├── load_file.py
│   ├── merge_router_info.py
│   ├── plot_date.py
│   └── process_general_info_date_type.py
├── .gitignore
├── README.md
└── requirements.txt
```

## Code Description
The functions have already been documented inside the python scripts. Therefore, this section will only briefly explain the main role of the three scripts used inside this test.
- [collect_kv_netbox.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/collect_kv_netbox.py): It calculates and returns the count of each feature stored in NetBox. The results are saved in `netbox_keys.yaml` under each manufacturer result directory. For example, part_number: 242 stored in result/arista/netbox_keys.yaml means that the key part_number appears 242 times for arista rotuers in NetBox.
- [extract_data_llm.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/extract_data_llm.py): It contains all the functions that interact with the OpenAI API.
- [filter_data_netbox.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/filter_data_netbox.py): It filters out irrelevant features from the NetBox dataset, retaining only the relevant ones in `filtered.yaml` for subsequent use.
- [grasp_cisco_router_series.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/grasp_cisco_router_series.py): It is specifically designed for Cisco routers and identifies the series of a given router. As a result, the Cisco router results include an additional directory level corresponding to the router series.
- [load_file.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/load_file.py): It provides fundamental functions for reading and writing files in various formats, such as PDF, JSON, CSV, and more.
- [merge_router_info.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/merge_router_info.py): It merges all the information from `filtered.yaml`, `general_llm.yaml`, `date_llm.yaml`, and `series.yaml` into a unified `merged.yaml`. Note that different routers may include different YAML files, which will be specifically explained in a later section.
- [plot_date.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/plot_date.py): It generates various relationship graphs based on the processed data.
- [process_general_info_date_type.py](https://gitlab.ethz.ch/nsg/research/powerdb/db_scrapping/-/blob/main/src/process_general_info_date_type.py): It extracts essential data from router URL datasheets with the assistance of LLM.

## Output Explanation
