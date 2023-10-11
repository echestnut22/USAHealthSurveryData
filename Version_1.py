import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
import pandas as pd
import numpy as np
import dash_bootstrap_components as dbc

df = pd.read_csv('USAHealthSurveryData/Nutrition_PhysicalActivity_Obesity_Cleaned.csv')


#Function for formula to find weighted percent
def calculate_weighted_mean_percent(df):
    numerator = sum(df['Percent'] * df['Sample_Size']/100)
    denominator = sum(df['Sample_Size'])
    return (numerator/denominator) * 100


# Create a new column 'Income Category' in the dataframe and map each income value to its category using the custom function
def map_income_to_category(income):
    if income in ['Less than $15,000', '$15,000 - $24,999']:
        return 'Low Income'
    elif income in ['$25,000 - $34,999', '$35,000 - $49,999']:
        return 'Middle Income'
    elif income in ['$50,000 - $74,999', '$75,000 or greater']:
        return 'High Income'
    

# Create a new column 'Income Category' in the dataframe and map each income value to its category using the custom function
df['Income Category'] = df['Income'].apply(map_income_to_category)

#Using a dictionary to rename question IDs for visualization
question_id_names = {
    'Q036': 'Are Obese',
    'Q037': 'Are Overweight',
    
    'Q047': 'Report No Physical Activity',
    'Q043': 'Report They Meet Aerobic Exercise Recommendations',
    'Q046': 'Report They Meet Strength Training Recommendations',
    'Q044': 'Report They Meet Both Aerobic Exercise and Strength Training Recommendations',
    'Q045': 'Report They Exceed Aerobic Exercise Recommendations',
    
    'Q018': 'Report They Consume No Fruits Daily',
    'Q019': 'Report They Consume No Vegetables Daily',
    
}

# Create a list of the question IDs in the desired order order for drop-down tabs
question_ids_ordered = ['Q036', 'Q037', 'Q047', 'Q043', 'Q046', 'Q044', 'Q045', 'Q018', 'Q019']

# Sort the dataframe by the QuestionID column using the list of question IDs in the desired order
df = df.sort_values('QuestionID', key=lambda x: x.map({k: i for i, k in enumerate(question_ids_ordered)}))

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container(
    fluid=True,
    children=[
        html.H1(children='USA Health Survey Data', style={'text-align': 'center', 'margin-top': '30px'}),
        dbc.Row([
            dbc.Col([
                html.Label('Question:'),
                dcc.Dropdown(
                    id='question-dropdown',
                    options=[{'label': question_id_names[qid], 'value': qid} for qid in df['QuestionID'].unique()],
                    value=df['QuestionID'].unique()[0]
                ),
            ], width=4),
            dbc.Col([
                html.Label('Filter by:'),
                dcc.Dropdown(
                    id='category-dropdown',
                    options=[{'label': 'Education', 'value': 'Education'}, {'label': 'Race/Ethnicity', 'value': 'Race/Ethnicity'}, {'label': 'Income', 'value': 'Income'}],
                    value='Education',
                    style={'width': '100%'}
                ),
            ], width=4),
            dbc.Col([
                html.Label('Filter value:'),
                dcc.Dropdown(
                    id='category-value-dropdown',
                    options=[{'label': 'All', 'value': 'All'}],
                    value='All',
                    style={'width': '100%'}
                ),
            ], width=4),
        ], style={'margin-bottom': '20px'}),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5(id='map-title')),
                    dbc.CardBody([
                        dcc.Graph(id='choropleth-map', config={'displayModeBar': False}),
                    ]),
                ], style={'border': '1px solid #d3d3d3'}),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5(id='chart-title')),
                    dbc.CardBody([
                        dcc.Graph(id='time-series-chart', config={'displayModeBar': False}),
                    ]),
                ], style={'border': '1px solid #d3d3d3'}),
            ], width=6),
        ]),
    ],
)

# Define the color scale to use based on the question ID. Shows inverse for exercise related questions so red=bad
def get_color_scale(question_id):
    if question_id in ['Q043', 'Q047','Q046','Q044','Q045','Q018','Q019']:
        return px.colors.sequential.OrRd[::-1]
    else:
        return px.colors.sequential.OrRd


    
# Define the callback function to update the category value dropdown based on the selected category.
@app.callback(
    Output('category-value-dropdown', 'options'),
    [Input('category-dropdown', 'value')]
)
def update_category_value_dropdown(category):
    if category == 'Education':
        options = [{'label': 'All', 'value': 'All'}] + [{'label': education, 'value': education} for education in df['Education'].dropna().unique()]
    elif category == 'Race/Ethnicity':
        options = [{'label': 'All', 'value': 'All'}] + [{'label': race, 'value': race} for race in df['Race/Ethnicity'].dropna().unique()]
    else:
        options = [{'label': 'All', 'value': 'All'}] + [{'label': income, 'value': income} for income in df['Income Category'].dropna().unique()]
    return options


# Define the callback function to update the choropleth map based on the selected question ID, category, and category value.
@app.callback(
    Output('choropleth-map', 'figure'),
    [Input('question-dropdown', 'value'),
     Input('category-dropdown', 'value'),
     Input('category-value-dropdown', 'value')]
)
def update_choropleth_map(question_id, category, category_value):
    #Updating question names from dictionary
    question_name = question_id_names[question_id]

    #Filter the DataFrame to only include rows for the selected question
    if category == 'Education':
        category_column = 'Education'
    elif category == 'Income':
        category_column = 'Income Category'
    else:
        category_column = 'Race/Ethnicity'

    if category_value == 'All':
        question_df = df[df['QuestionID'] == question_id]
    else:
        question_df = df[(df['QuestionID'] == question_id) & (df[category_column] == category_value)]

    # Compute the average percent for each state, weighted by sample size, for all available years
    # Reset index 
    state_avg_percents = question_df.groupby(['Year', 'LocationAbbr']).apply(lambda x: calculate_weighted_mean_percent(x)).reset_index(name='Percent')


    # Compute the minimum and maximum average percent values for the selected question across all years
    percent_min = df[df['QuestionID'] == question_id]['Percent'].min()
    percent_max = df[df['QuestionID'] == question_id]['Percent'].max()

    # Define the color scale to use based on the selected question ID
    color_scale = get_color_scale(question_id)

    hover_text = []
    for state, percent in zip(state_avg_percents['LocationAbbr'], state_avg_percents['Percent']):
        hover_text.append(f"{state}: {percent:.2f}%")

    # Create a choropleth map of the average percent by state for all years
    fig = px.choropleth(locations=state_avg_percents['LocationAbbr'], 
                locationmode="USA-states", 
                color=state_avg_percents['Percent'],
                animation_frame=state_avg_percents['Year'], 
                scope="usa", 
                color_continuous_scale=color_scale,
                range_color=(percent_min, percent_max),
                title=f"Percent of {category_value} Adults That {question_name} from {df['Year'].min()} to {df['Year'].max()}",
                custom_data=[hover_text],
                hover_name=state_avg_percents['LocationAbbr'] +': ' + state_avg_percents['Percent'].round(2).astype(str) + '%'
                        ) 
    fig.update_traces(hovertemplate="<b>%{customdata}</b><br>")
    fig.update_layout(coloraxis_colorbar=dict(title="Percent"))


    return fig

# Define the callback function to update the time series chart based on the selected state, question ID, category, and category value.
@app.callback(
    Output('time-series-chart', 'figure'),
    [Input('choropleth-map', 'clickData'),
     Input('question-dropdown', 'value'),
     Input('category-dropdown', 'value'),
     Input('category-value-dropdown', 'value')]
)
def update_time_series_chart(clickData, question_id, category, category_value):
    #Updating question names from dictionary
    question_name = question_id_names[question_id]

    if clickData is not None:
        # Get the abbreviation of the clicked state
        state_abbrev = clickData['points'][0]['location']

        # Filter the DataFrame to only include rows for the selected question ID and state
        question_state_df = df[(df['QuestionID'] == question_id) & (df['LocationAbbr'] == state_abbrev)]

        if category != 'None' and category_value != 'All':
            if category == 'Education':
                category_column = 'Education'
            elif category == 'Income':
                category_column = 'Income Category'
            else:
                category_column = 'Race/Ethnicity'

            # Filter the DataFrame to only include rows for the selected category value
            question_state_df = question_state_df[question_state_df[category_column] == category_value]

        # Some question IDs do not have data for every state
        if question_state_df.empty:
            return {
            'data': [],
            'layout': {
            'title': f"No data available for {state_abbrev} and Question {question_id}",
            'xaxis': {'title': 'Year'},
            'yaxis': {'title': 'Percent'}
            }}

        # Compute the weighted mean percent for each year
        year_weighted_means = question_state_df.groupby('Year').apply(lambda x: calculate_weighted_mean_percent(x))

        # Create a line chart of the percent by year for the selected state, question ID, category, and category value
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=year_weighted_means.index, y=year_weighted_means.values))
        fig.update_layout(title=f"Percent Change Over Time For {category_value} Adults That {question_name} in {state_abbrev}",
                          xaxis_title="Year", yaxis_title="Percent")
        fig.update_xaxes(tickmode='array', tickvals=list(range(2011, 2022, 2)), 
                         ticktext=[str(year) for year in range(2011, 2022, 2)])
        #Make percent round to two decimal places 
        fig.update_layout(yaxis=dict(tickformat=".2f"))
        return fig

    # If no state is selected, return a message
    return {
        'data': [],
        'layout': {
            'title': f"Click a State to See Percent Change Over Time For {category_value} Adults That {question_name}",
            'xaxis': {'title': 'Year'},
            'yaxis': {'title': 'Percent'}
        }
    }


if __name__ == '__main__':
    app.run_server()
