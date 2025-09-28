# -*- coding: utf-8 -*-
"""
Created on Tue May  7 12:37:55 2024

@author: Joonsoo
"""
#### Packages
import streamlit as st
import altair as alt
import numpy as np
import pandas as pd
import os
import requests
from fredapi import Fred
import matplotlib.pyplot as plt

print(st.__version__)

#### API Keys
#os.environ["ANTHROPIC_API_ID"] = st.secrets["ANTHROPIC_API_KEY"]

#### Data import
#fred_api_key_input = st.secrets["fred_api_key"]

### API key
#fred_api_key_input = st.secrets["fred_api_key"]
fred_api_key_input = '7a3a846e27994737590201d1ed80f0f1'
fred = Fred(api_key = fred_api_key_input)

### Global price of Coffee, Robustas
df_robus = fred.get_series('PCOFFROBUSDM')
df_robus.name = 'robustas'

### Global price of Coffee, Other Mild Arabica
df_arabica = fred.get_series('PCOFFOTMUSDM')
df_arabica.name = 'arabica'

#### Data transformation
### Join data sources
df = pd.merge(
    df_robus, 
    df_arabica,
    left_index = True
    ,right_index = True)

### Data format changes
df['Close Date'] = df.index
df['Close Date'] = df['Close Date'].dt.strftime("%Y-%m-%d")
df = df.round(2)

### Rename column names
new_column_names = {
    "robustas": "Robusta",
    "arabica": "Arabica"
}
df = df.rename(columns = new_column_names)

### Add columns to df object to calculate M-over-M delta
df['Robusta Chg'] = df['Robusta']/df['Robusta'].shift(1) - 1
df['Arabica Chg'] = df['Arabica']/df['Arabica'].shift(1) - 1

### Data range filtering - last 48 months
df_range = 48

#### Altair package - data object for basic line chart
#### Time-series line chart for monthly bean prices
### Data range filter and create df_base object
df_base = df.tail(df_range)

### Melt the DataFrame to convert it to long format
df_base = df_base[['Close Date', 'Robusta', 'Arabica',]]

#### Make sure 'Close Date' is datetime
df_base["Close Date"] = pd.to_datetime(df_base["Close Date"])

#### Normalize to midnight to avoid time shift issues
df_base["Close Date"] = pd.to_datetime(df_base["Close Date"]).dt.floor('D')

#### Add exactly 1 day
df_base["Close Date"] = df_base["Close Date"] + pd.Timedelta(days = 0.7)

melted_df_base = df_base.melt(
    id_vars = "Close Date", 
    var_name = "Bean Type", 
    value_name = "Price",
)

### Output columns
output_list = ["Robusta", "Arabica"]

### Define range:
## Determine the minimum and maximum values of 'Robusta' or 'Arabica'
min_y_value = melted_df_base["Price"].min()
max_y_value = melted_df_base["Price"].max()

### Starting and end points for the Y-axis range
y_start = np.floor(min_y_value * 0.9) / 2
y_end = np.ceil(max_y_value * 2.1) / 2

### Make radio button less cramped by adding a space after each label
labels = [option + " " for option in output_list]
input_dropdown = alt.binding_radio(
    # Add the empty selection which shows all when clicked
    options=output_list + [None],
    labels=labels + ["All"],
    name="Bean Type: ",
)
selection = alt.selection_point(
    fields=["Bean Type"],
    bind=input_dropdown,
)

### Display basic line chart
base_chart = (
    alt.Chart(melted_df_base).mark_line()
    .encode(
        x = alt.X(
            "Close Date:T",   # bucket into month-year
            axis = alt.Axis(title = "Close Date", format = "%b-%Y")  # MMM-YYYY format
        ),
        y = alt.Y(
            "Price:Q", 
            scale = alt.Scale(domain = [y_start, y_end])
        ),
        color = alt.Color("Bean Type:N", sort = output_list),
        # tooltip=['Ticker:N', 'Yield:Q']
    )
    .add_params(selection)
    .transform_filter(selection)
)

### Add interactive vertical line
selector = alt.selection_single(
    encodings = ["x"],  # Selection based on x-axis (Close Date)
    on = "mouseover",  # Trigger on mouseover
    nearest = True,  # Select the value nearest to the mouse cursor
    empty = "none",  # Don't show anything when not mousing over the chart
)
rule = (
    alt.Chart(melted_df_base)
    .mark_rule()
    .encode(
        x = "Close Date:T",
        opacity = alt.condition(selector, alt.value(1), alt.value(0)),
        color = alt.value("gray"),
    )
    .add_selection(selector)
)

### Add text annotations for Ticker and Yield at intersection
## This step might require adjusting depending on your DataFrame's structure
text = (
    base_chart.mark_text(
        align = "left",
        dx = 5, 
        dy = -10, 
        fontWeight = "bold", 
        fontSize = 15)
    .encode(text=alt.condition(
        selector, 
        "Price:Q", 
        alt.value(" "), 
        format=".2f"))
    .transform_filter(selector)
)

### Assuming 'melted_df_base' has a 'Close Date' column in datetime format
start_date = melted_df_base["Close Date"].min()
end_date = melted_df_base["Close Date"].max()

### Generate quarter start dates within the range of your data
quarter_starts = pd.date_range(
    start = start_date, 
    end = end_date, 
    freq="QS").to_series()
quarter_starts_df = pd.DataFrame({"Close Date": quarter_starts})

### Chart for bold vertical lines at each quarter start
quarter_lines = (
    alt.Chart(quarter_starts_df).mark_rule(
        color="gray",
        strokeWidth=1
    )  # Bold vertical lines, adjust color/strokeWidth as needed
    .encode(x="Close Date:T")
)

### Combine the charts
final_chart_base = alt.layer(base_chart, rule, text, quarter_lines)

#### Altair package - data object for M-over-M line chart
#### M-over-M time-series line chart for monthly bean prices
### Add columns to df object to calculate M-over-M delta
df_chg_col_list = ['Close Date', 'Robusta Chg', 'Arabica Chg']

### Rename column names and create df_chg data object
df_chg = df[df_chg_col_list].tail(df_range)
new_column_names = {
    "Robusta Chg": "Robusta",
    "Arabica Chg": "Arabica"
}
df_chg = df_chg.rename(columns = new_column_names)

#### Make sure 'Close Date' is datetime
df_chg["Close Date"] = pd.to_datetime(df_chg["Close Date"])

#### Add exactly 1 day
df_chg["Close Date"] = df_chg["Close Date"] + pd.Timedelta(days = 0.7)


### Melt the DataFrame to convert it to long format
melted_df_chg = df_chg.melt(
    id_vars = "Close Date", 
    var_name = "Bean Type", 
    value_name = "Change"
)
### Rename output columns
output_list = ["Robusta", "Arabica"]

### Define range:
## Determine the minimum and maximum values of 'Robusta' or 'Arabica' deltas
min_y_value = melted_df_chg["Change"].min()
max_y_value = melted_df_chg["Change"].max()

### Calculate the starting and end points for the Y-axis range
y_start = (min_y_value * 2.2) / 2
y_end = (max_y_value * 2.2) / 2

### Make radio button less cramped by adding a space after each label
labels = [option + " " for option in output_list]
input_dropdown = alt.binding_radio(
    # Add the empty selection which shows all when clicked
    options=output_list + [None],
    labels=labels + ["All"],
    name="Bean Type: ",
)
selection = alt.selection_point(
    fields=["Bean Type"],
    bind=input_dropdown,
)

### Basic bar chart
base_chart = (
    alt.Chart(melted_df_chg).mark_bar(size = 2.5)  # controls thickness
    .encode(
        # Use temporal with formatting
        x = alt.X(
            "yearmonth(Close Date):T", 
            axis = alt.Axis(title = "Close Date", format = "%b-%Y")  # MMM-YYYY format
        ),
        y = alt.Y(
            "Change:Q",
            scale = alt.Scale(domain = [y_start, y_end]),
            axis = alt.Axis(format = "%")
        ),
        color = alt.Color("Bean Type:N", sort = output_list),
        xOffset = "Bean Type:N"   # side-by-side bars by Bean Type
        # tooltip=['Ticker:N', 'Yield:Q']
    )
    .add_params(selection)
    .transform_filter(selection)
)

### Add interactive vertical line
selector = alt.selection_single(
    encodings = ["x"],  # Selection based on x-axis (Close Date)
    on = "mouseover",  # Trigger on mouseover
    nearest = True,  # Select the value nearest to the mouse cursor
    empty = "none",  # Don't show anything when not mousing over the chart
)
rule = (
    alt.Chart(melted_df_chg)
    .mark_rule()
    .encode(
        x = "Close Date:T",
        opacity = alt.condition(selector, alt.value(1), alt.value(0)),
        color = alt.value("gray"),
    )
    .add_selection(selector)
)

### Add text annotations for Ticker and Yield at intersection
## This step might require adjusting depending on your DataFrame's structure
text = (
    base_chart.mark_text(
        align = "left",
        dx = 5, 
        dy = -10, 
        fontWeight = "bold", 
        fontSize = 15)
    .encode(text=alt.condition(
        selector, 
        "Change:Q", 
        alt.value(" "), 
        format = ".1%"))
    .transform_filter(selector)
)

### Assuming 'melted_df_chg' has a 'Close Date' column in datetime format
start_date = melted_df_chg["Close Date"].min()
end_date = melted_df_chg["Close Date"].max()

### Generate quarter start dates within the range of your data
quarter_starts = pd.date_range(
    start = start_date, 
    end = end_date, 
    freq = "QS").to_series()
quarter_starts_df = pd.DataFrame({"Close Date": quarter_starts})

### Chart for bold vertical lines at each quarter start
quarter_lines = (
    alt.Chart(quarter_starts_df).mark_rule(
        color="gray",
        strokeWidth=1
    )  # Bold vertical lines, adjust color/strokeWidth as needed
    .encode(x = "Close Date:T")
)

### Chart for 0% horizontal line
y_zero = (
    alt.Chart(pd.DataFrame({'Change':[0]})).mark_rule(
        color = 'black',
        size = 3)
    .encode(y = "Change"))

## Combine the charts
final_chart_chg = alt.layer(base_chart, rule, text, quarter_lines, y_zero)

### Summary statistics
## Data pre-proc
df_summary_stat = df.tail(48).describe().loc[['mean', 'std', 'min', '25%', '50%', '75%', 'max']]
df_summary_stat = df_summary_stat.round(2)

## Data type update
df_summary_stat['Robusta Chg'] = df_summary_stat['Robusta Chg'].map('{:.1%}'.format)
df_summary_stat['Arabica Chg'] = df_summary_stat['Arabica Chg'].map('{:.1%}'.format)

### Side bar data
## Data filteration
df_sidebar = df[['Close Date', 'Robusta', 'Robusta Chg', 'Arabica', 'Arabica Chg']].tail(6)

## Data type update
df_sidebar['Robusta Chg'] = df_sidebar['Robusta Chg'].map('{:.1%}'.format)
df_sidebar['Arabica Chg'] = df_sidebar['Arabica Chg'].map('{:.1%}'.format)


#######################################################################################################
#### Streamlit visualization
### Headers
st.set_page_config(page_title = "Coffee-flation", page_icon="☕")
st.title("Coffee-flation Dashboard :coffee:")
st.text("This open-source dashboard aids small coffee roasters \nin optimizing cost efficiency by providing insights into \nthe price fluctuations of essential coffee beans. \n\nWe believe that technology should serve our local businesses!")
st.write(f"Developed and distributed by [**LookUp Consulting LLC**](https://www.lookupconsultancy.com/)")

### Line chart - base chart
st.header("Global price of coffee - monthly trends", divider = "gray")
st.text("(Units: U.S. Cents per Pound)")

## Draw a chart
st.altair_chart(
    final_chart_base,
    theme = None,
    #theme = "streamlit",
    use_container_width = True,
)

### Line chart - base chart
## Set the title and labels
## Display line chart in streamlit
st.header("Global price of coffee - monthly changes", divider = "gray")
st.text("(Units: Percentage)")

## Draw a chart
st.altair_chart(
    final_chart_chg,
    #theme = None,
    theme = "streamlit",
    use_container_width = True,
)

### Summary statistics
st.header("Global price of coffee - summary statistics", divider = "gray")
st.write(df_summary_stat[['Robusta', 'Arabica', 'Robusta Chg', 'Arabica Chg']])

#### Sidebard
with st.sidebar:
    # Show the filtered DataFrame
    # Displaying a table
    st.subheader("Global coffee prices - past 6 months")
    st.dataframe(df_sidebar, hide_index = True)
    #st.write(df_sidebar.tail(6), width = 400, hide_index = True)

    # Source
    todays_date = str(df.tail(1)['Close Date'][0])

    link1 = "https://fred.stlouisfed.org/series/PCOFFROBUSDM"
    link2 = "https://fred.stlouisfed.org/series/PCOFFROBUSDM"
    link3 = "https://fred.stlouisfed.org/series/PCOFFOTMUSDM"

    st.write(f"Data sources: International Monetary Fund, Global price of Coffee, Robustas [PCOFFROBUSDM], Global price of Coffee, Other Mild Arabica [PCOFFOTMUSDM] retrieved from FRED, [Federal Reserve Bank of St. Louis]({link1}) as of {todays_date}.")
    st.write(
        f"Global price of Coffee, Robustas: [PCOFFROBUSDM]({link2}), Global price of Coffee, Arabica: [PCOFFOTMUSDM]({link3})"
    )