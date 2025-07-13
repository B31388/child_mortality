import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go

# Load and process data
mort = pd.read_csv('/workspaces/child_mortality/Datasets/child_mortality.csv')
edu = pd.read_csv('/workspaces/child_mortality/Datasets/female_education.csv')
san = pd.read_csv('/workspaces/child_mortality/Datasets/sanitation_services.csv')

# Reshape data
def reshape_wide_to_long(df, value_name):
    return df.melt(
        id_vars=['Country', 'Indicator Name'],
        value_vars=['2018', '2019', '2020', '2021', '2022'],
        var_name='year',
        value_name=value_name
    ).drop(columns=['Indicator Name'])

mort_long = reshape_wide_to_long(mort, 'Mortality rate, under-5 (per 1,000 live births)')
edu_long = reshape_wide_to_long(edu, 'Educational attainment, at least completed lower secondary, population 25+, female (%) (cumulative)')
san_long = reshape_wide_to_long(san, 'People using at least basic sanitation services (% of population)')

# Merge data for correlations
df = (mort_long
      .merge(edu_long, on=['Country', 'year'], how='inner')
      .merge(san_long, on=['Country', 'year'], how='inner'))

# Convert year to integer
df['year'] = df['year'].astype(int)

# Rename columns
df = df.rename(columns={
    'Mortality rate, under-5 (per 1,000 live births)': 'U5MR',
    'Educational attainment, at least completed lower secondary, population 25+, female (%) (cumulative)': 'FemaleEdu',
    'People using at least basic sanitation services (% of population)': 'Sanitation'
})

# Handle missing values in FemaleEdu
df = df.sort_values(['Country', 'year']).reset_index(drop=True)
df['FemaleEdu'] = (
    df.groupby('Country')['FemaleEdu']
      .transform(lambda g: g.interpolate(method='linear'))
      .ffill()
      .bfill()
)

# Save processed data
df.to_csv('processed_data.csv', index=False)

# Subset for U5MR-only visualizations
df_u5mr = df[['Country', 'year', 'U5MR']]

# Initialize Dash app
app = Dash(__name__)

# CSS for Roboto font
app.css.append_css({
    'external_url': 'https://fonts.googleapis.com/css2?family=Roboto&display=swap'
})

# Create initial visualizations
fig_u5mr = px.line(df_u5mr, x='year', y='U5MR', color='Country',
                    title='Under-5 Mortality Rate (per 1,000 live births), 2018–2022')

fig_u5mr_map = px.choropleth(df_u5mr[df_u5mr.year == 2022], locations='Country',
                             color='U5MR', title='2022 Under-5 Mortality Rate',
                             locationmode='country names', color_continuous_scale='Viridis')

# Correlation heatmap (U5MR, FemaleEdu, Sanitation)
corr_matrix = df[['U5MR', 'FemaleEdu', 'Sanitation']].corr()
fig_heatmap = go.Figure(data=go.Heatmap(
    z=corr_matrix.values,
    x=corr_matrix.columns,
    y=corr_matrix.index,
    colorscale='Blues',
    zmin=-1, zmax=1,
    text=corr_matrix.values.round(2),
    texttemplate='%{text}',
    textfont={'size': 12}
))
fig_heatmap.update_layout(
    title='Correlation of U5MR, Female Education, and Sanitation (2018–2022)',
    xaxis_nticks=3, yaxis_nticks=3,
    width=500, height=400
)

fig_bar = px.bar(df_u5mr[df_u5mr.year == 2022], x='Country', y='U5MR',
                 title='Under-5 Mortality Rate Comparison (2022)',
                 color='Country')

# Country and year options
country_options = [{'label': country, 'value': country} for country in df_u5mr['Country'].unique()]
year_options = sorted(df_u5mr['year'].unique())
marks = {int(year): str(year) for year in year_options}

# Narrative text
intro_text = """
# Unequal Beginnings: Child Mortality Trends in Sub-Saharan Africa
In Sub-Saharan Africa, under-5 mortality remains a critical challenge, with 58% of global under-5 deaths in 2023 occurring in this region (UNICEF, 2025). This dashboard explores temporal and spatial trends in under-5 mortality rates (U5MR) for Ethiopia, Kenya, and Nigeria from 2018 to 2022, alongside correlations with female education and sanitation access. Use the dropdown and slider to filter countries and years, revealing trends, spatial patterns, and key relationships driving child mortality.
"""

# Blue theme styles
theme = {
    'background': '#1E3A8A',  # Dark blue background
    'text': '#FFFFFF',  # White text
    'accent': '#3B82F6',  # Medium blue for headers/tabs
    'light': '#93C5FD',  # Light blue for subtle accents
    'font': 'Roboto, sans-serif'
}

# App layout with Z-pattern
app.layout = html.Div([
    # Top: Narrative
    dcc.Markdown(intro_text, style={
        'padding': '20px', 'textAlign': 'center',
        'backgroundColor': theme['background'], 'color': theme['text'],
        'fontFamily': theme['font'], 'borderRadius': '5px',
        'marginBottom': '20px'
    }),
    
    # Top-Middle: Filters (side by side for Z-flow)
    html.Div([
        html.Div([
            html.Label("Select Countries:", style={
                'marginRight': '10px', 'color': theme['text'], 'fontFamily': theme['font']
            }),
            dcc.Dropdown(id='country-dropdown', options=country_options, value=df_u5mr['Country'].unique().tolist(),
                         multi=True, style={
                             'width': '100%', 'backgroundColor': theme['light'],
                             'color': '#000000', 'fontFamily': theme['font']
                         })
        ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'}),
        html.Div([
            html.Label("Select Year for Map and Bar Chart:", style={
                'marginRight': '10px', 'color': theme['text'], 'fontFamily': theme['font']
            }),
            dcc.Slider(id='year-slider', min=min(year_options), max=max(year_options), step=1,
                       value=2022, marks=marks,
                       tooltip={'placement': 'bottom', 'always_visible': True})
        ], style={'width': '45%', 'display': 'inline-block', 'padding': '10px'}),
    ], style={
        'display': 'flex', 'justifyContent': 'space-between',
        'backgroundColor': theme['background'], 'borderRadius': '5px',
        'marginBottom': '20px'
    }),
    
    # Middle-Bottom: Tabs with visualizations
    dcc.Tabs([
        dcc.Tab(label='Temporal Trends (2018–2022)', children=[
            html.Div([
                dcc.Graph(id='u5mr-graph', figure=fig_u5mr, style={
                    'width': '100%', 'padding': '10px',
                    'backgroundColor': '#FFFFFF', 'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                }),
            ], style={'padding': '10px'}),
        ], style={'backgroundColor': theme['accent'], 'color': theme['text'], 'fontFamily': theme['font']}),
        dcc.Tab(label='Spatial Trends', children=[
            html.Div([
                dcc.Graph(id='u5mr-map', figure=fig_u5mr_map, style={
                    'width': '100%', 'padding': '10px',
                    'backgroundColor': '#FFFFFF', 'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
                }),
            ], style={'padding': '10px'}),
        ], style={'backgroundColor': theme['accent'], 'color': theme['text'], 'fontFamily': theme['font']}),
        dcc.Tab(label='Correlations & Comparisons', children=[
            html.Div([
                dcc.Graph(id='heatmap', figure=fig_heatmap, style={
                    'padding': '10px', 'backgroundColor': '#FFFFFF',
                    'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'width': '50%', 'display': 'inline-block'
                }),
                dcc.Graph(id='bar-chart', figure=fig_bar, style={
                    'padding': '10px', 'backgroundColor': '#FFFFFF',
                    'borderRadius': '5px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'width': '50%', 'display': 'inline-block'
                }),
            ], style={'display': 'flex', 'padding': '10px'}),
        ], style={'backgroundColor': theme['accent'], 'color': theme['text'], 'fontFamily': theme['font']}),
    ], style={'padding': '10px', 'backgroundColor': theme['light'], 'borderRadius': '5px'}),
], style={'maxWidth': '1200px', 'margin': 'auto', 'backgroundColor': theme['background'], 'fontFamily': theme['font']})

# Callback for dynamic updates
@app.callback(
    [Output('u5mr-graph', 'figure'),
     Output('u5mr-map', 'figure'),
     Output('bar-chart', 'figure')],
    [Input('country-dropdown', 'value'),
     Input('year-slider', 'value')]
)
def update_charts(selected_countries, selected_year):
    filtered_df = df_u5mr[df_u5mr['Country'].isin(selected_countries)]
    
    # Line chart (all years, filtered by countries)
    fig_u5mr = px.line(filtered_df, x='year', y='U5MR', color='Country',
                        title='Under-5 Mortality Rate (per 1,000 live births), 2018–2022')
    
    # Choropleth map (filtered by year and countries)
    map_df = filtered_df[filtered_df['year'] == selected_year]
    fig_u5mr_map = px.choropleth(map_df, locations='Country', color='U5MR',
                                 title=f'{selected_year} Under-5 Mortality Rate',
                                 locationmode='country names', color_continuous_scale='Viridis')
    
    # Bar chart (filtered by year and countries)
    fig_bar = px.bar(map_df, x='Country', y='U5MR',
                     title=f'Under-5 Mortality Rate Comparison ({selected_year})',
                     color='Country')
    
    return fig_u5mr, fig_u5mr_map, fig_bar

# Run the app
if __name__ == '__main__':
    app.run(debug=True)