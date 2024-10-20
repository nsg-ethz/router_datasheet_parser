import json
import random
import os
from typing import Literal, Optional

import pandas as pd
import requests
import tiktoken
from markdownify import markdownify as md
from openai import OpenAI
from pydantic import BaseModel, Field
from tqdm import tqdm

# Set random seed
random.seed(40)

""" 
Prompting strategies
    https://platform.openai.com/docs/guides/prompt-engineering
Structured outputs:
    https://towardsdatascience.com/diving-deeper-with-structured-outputs-b4a5d280c208?gi=112518943760
"""

class Power(BaseModel):
    value: int = Field(description="The value in watts")
    additional_info: Optional[str] = Field(description="Any additional information that may be associated with the power value (such as the temperature, throughput, ...)")
class RouterData(BaseModel):
    name: str = Field(description="The name of the router model")
    typical_power: Optional[Power] = Field(description="The typical power consumption of the router")
    max_power: Optional[Power] = Field(description="The maximum power consumption of the router")
    release_date: Optional[str] = Field(description="Day the router series was released (YYYY-MM-DD format)")
    psu_rating: Optional[Literal["Bronze", "Silver", "Gold", "Platinum"]] = Field(description="If provided, the rating of the router's Power Supply Unit (PSU)")
#print(json.dumps(BugReport.model_json_schema(), indent=2))

PERSONA         =   "You are an expert network engineer."
HIGH_LEVEL_TASK =   "You are trying to gather data on the Power Supply Units (PSUs) of routers on your network. " \
                    "To this end you will need to scan through the data sheet of the routers and extract the relevant information." 
LOW_LEVEL_TASK  =   lambda name: f"I will give you the data sheet containing the information you are after. You are looking for the data relevant to router {name}.\n" \
                    "Your task, for the data sheet, is to use your expertise and the " \
                    "information I provided to try to extract the information and fill out the fields of the given structure. " \
                    "If the information is not present, you can leave the field empty. If you are unsure, leave the field empty.\n" \
                    "Only use the information contained in the data sheet."

# For future reference, can build Lambdas into this using: TEXT_AMOUNT = lambda amount: f'text {amount}'
system_prompt = lambda name: "\n".join([PERSONA, HIGH_LEVEL_TASK, LOW_LEVEL_TASK(name)])


if __name__ == "__main__":
    client = OpenAI()
    # Import csv file
    df = pd.read_csv("network_devices_db.csv", index_col=0)
    # Create a data structure to hold the information
    data = {}
    for name, row in tqdm(df.iterrows(), total=df.shape[0]):
        # Grab the model name and URL
        url = row["Datasheet URL"]
        if pd.isna(url):
            continue
        print(f"Looking into the datasheet of router: {name}")
        # Grab the HTML content of the datasheet
        html_content = requests.get(url).text
        # Convert the HTML content to markdown
        markdown_content = md(html_content)
        # Save the markdown content to a file
        os.makedirs("markdown", exist_ok=True)
        with open(f"markdown/{name}.md", "w") as f:
            f.write(markdown_content)
        # Check the difference in token length for both the HTML and markdown content
        encoding = tiktoken.encoding_for_model("gpt-4o")
        #print(f"HTML token length: {len(encoding.encode(html_content))}")
        print(f"Markdown token length: {len(encoding.encode(markdown_content))}")
        # Query the model with the markdown content
        try:
            completion = client.beta.chat.completions.parse(
                temperature=0,
                model="gpt-4o-2024-08-06", #"gpt-4o-mini", #"gpt-4o-2024-08-06", 
                messages=[ 
                    {
                        "role": "system", 
                        "content": system_prompt(name)
                    },
                    {
                        "role": "user",
                        "content": markdown_content
                    }
                ],
                response_format=RouterData,
            )

            # Get the output from your API call
            output = completion.choices[0].message.parsed
            # Dump the model to a dictionary with JSON-compatible formatting
            output_dict = output.model_dump(mode='json')
            # Print the dictionary with indentation using json.dumps()
            output = json.dumps(output_dict, indent=4)
            #print(output)
            data[name] = output_dict
        except Exception as e:
            print(f"Error: {e}")
            pass
        
    # Save the data to a file
    with open("data.json", "w") as f:
        json.dump(data, f, indent=4)
