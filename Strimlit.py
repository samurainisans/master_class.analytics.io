import pandas as pd
import json
import pydeck as pdk
import geopandas as gpd
import plotly.express as px
import streamlit as st

st.set_page_config(layout="wide")

@st.cache_data
def load_data():
    with open("enriched_masterclasses.json", "r", encoding='utf-8') as f:
        data = json.load(f)
    df = pd.json_normalize(data)
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['registration_deadline'] = pd.to_datetime(df['registration_deadline'])
    return df

@st.cache_data
def load_geojson():
    gdf = gpd.read_file("output.geojson")
    return gdf

def filter_geodata(gdf, category, start_time):
    gdf_filtered = gdf.copy()
    if category:
        gdf_filtered = gdf_filtered[gdf_filtered['categories'].apply(
            lambda x: any(item in x for item in category))]
    if start_time:
        gdf_filtered = gdf_filtered[(gdf_filtered['start_time'] >= pd.to_datetime(start_time[0])) &
                                    (gdf_filtered['start_time'] <= pd.to_datetime(start_time[1]))]
    return gdf_filtered

def show_map(gdf):
    st.write("## Карта мероприятий:", "Показаны места проведения выбранных мероприятий.")

    tooltip = {
        "html": "<b>Название:</b> {title}<br/>"
                "<b>Место:</b> {location_name}<br/>"
                "<b>Категории:</b> {categories_str}<br/>",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }

    gdf['categories_str'] = gdf['categories'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

    view_state = pdk.ViewState(
        latitude=55.755864,
        longitude=37.617698,
        zoom=5,
        pitch=0,
        width=1200,
        height=600,
    )

    layers = [
        pdk.Layer(
            'GeoJsonLayer',
            data=gdf,
            get_point_radius=10000,
            get_fill_color='[200, 30, 0, 160]',
            pickable=True,
            auto_highlight=True,
        )
    ]

    r = pdk.Deck(
        map_style='mapbox://styles/mapbox/light-v9',
        initial_view_state=view_state,
        layers=layers,
        tooltip=tooltip,
        map_provider='mapbox',
    )

    st.pydeck_chart(r)

def plot_histogram(df, column, sort_by):
    st.write(f"## Распределение мастер-классов по {column}",
             "График показывает количественное распределение мастер-классов.")
    count_df = df[column].value_counts().reset_index()
    count_df.columns = [column, 'count']
    if sort_by == 'по возрастанию':
        count_df = count_df.sort_values(by='count', ascending=True)
    else:
        count_df = count_df.sort_values(by='count', ascending=False)
    fig = px.bar(count_df, y=column, x='count', orientation='h', title=f'Распределение мастер-классов по {column}',
                 labels={'count': 'Количество мастер-классов', f'{column}': column})
    fig.update_layout(width=1200, height=800, title_font_size=40, xaxis_title_font_size=30, yaxis_title_font_size=30,
                      legend_title_font_size=30, legend_font_size=24)
    fig.update_traces(textfont_size=20)
    st.plotly_chart(fig)

df = load_data()
df['categories'] = df['categories'].apply(lambda x: x if isinstance(x, list) else [])
gdf = load_geojson()

option = st.selectbox(
    'Выберите тип данных для графика:',
    ('Категории', 'Временной диапазон', 'Регионы', 'Города')
)
sort_by = st.radio("Выберите порядок сортировки:", ['по возрастанию', 'по убыванию'])

category = st.sidebar.multiselect('Выберите категорию:', df['categories'].explode().unique(),
                                  placeholder='Выберите категорию(и)')
start_time = st.sidebar.slider('Выберите временной диапазон:',
                               min_value=df['start_time'].min().to_pydatetime(),
                               max_value=df['start_time'].max().to_pydatetime(),
                               value=(df['start_time'].min().to_pydatetime(), df['start_time'].max().to_pydatetime()),
                               format="DD-MM-YYYY")

filtered_df = df
if category:
    filtered_df = filtered_df[filtered_df['categories'].apply(lambda x: any(item in x for item in category))]
if start_time:
    filtered_df = filtered_df[(filtered_df['start_time'] >= pd.to_datetime(start_time[0])) &
                              (filtered_df['start_time'] <= pd.to_datetime(start_time[1]))]
filtered_gdf = filter_geodata(gdf, category, start_time)

if option == 'Категории':
    category_counts = filtered_df['categories'].explode().value_counts()
    total_count = category_counts.sum()
    category_percentages = category_counts / total_count * 100
    small_categories = category_percentages[category_percentages <= 5].index
    other_percentage = category_percentages[small_categories].sum()
    category_counts['Остальные'] = other_percentage
    category_counts = category_counts.drop(small_categories)
    category_counts = category_counts[category_counts > 0]
    st.write("## Распределение мастер-классов по категориям",
             "График показывает распределение мастер-классов по категориям.")
    fig = px.pie(values=category_counts, names=category_counts.index)
    fig.update_traces(textinfo='percent', textposition='inside', textfont=dict(size=45))
    fig.update_layout(height=850, width=1400, legend_title_font_size=36, legend_font_size=36)
    st.plotly_chart(fig)
elif option == 'Временной диапазон':
    df_time_grouped = filtered_df.groupby(filtered_df['start_time'].dt.date).count()['title'].reset_index()
    df_time_grouped.columns = ['start_time', 'count']
    st.write("## Распределение мастер-классов по времени", "График показывает распределение мастер-классов по времени.")
    fig = px.line(df_time_grouped, x='start_time', y='count', title='Распределение мастер-классов по времени',
                  labels={'start_time': 'Дата', 'count': 'Количество мастер-классов'})
    fig.update_xaxes(dtick="M1", tickformat="%b\n%Y")
    fig.update_layout(height=600, width=800, title_font_size=40, xaxis_title_font_size=30, yaxis_title_font_size=30,
                      legend_title_font_size=30, legend_font_size=24)
    fig.update_traces(textfont_size=20)
    st.plotly_chart(fig)

elif option == 'Регионы':
    plot_histogram(filtered_df, 'province', sort_by)
elif option == 'Города':
    plot_histogram(filtered_df, 'locality', sort_by)

st.write(filtered_df[['title', 'location_name', 'start_time', 'categories']])
show_map(filtered_gdf)

def analyze_speakers(df, sort_by):
    all_speakers = []
    for index, row in df.iterrows():
        for speaker in row['speakers']:
            all_speakers.append(speaker['name'])

    speaker_counts = pd.Series(all_speakers).value_counts().reset_index()
    speaker_counts.columns = ['Speaker', 'Events']

    if sort_by == 'по возрастанию':
        speaker_counts = speaker_counts.sort_values(by='Events', ascending=True)
    else:
        speaker_counts = speaker_counts.sort_values(by='Events', ascending=False)

    st.write("## Спикеры", "График показывает распределение спикеров по мастер-классам.")
    fig = px.bar(speaker_counts, x='Events', y='Speaker', orientation='h',
                 title='Частота участия спикеров в мастер-классах', labels={
            'Speaker': 'Спикер',
            'Events': 'Количество мастер-классов'
        })
    fig.update_layout(width=1200, height=800, title_font_size=40, xaxis_title_font_size=36, yaxis_title_font_size=36,
                      legend_title_font_size=30, legend_font_size=24)
    fig.update_traces(textfont_size=24)
    st.plotly_chart(fig)

analyze_speakers(filtered_df, sort_by)

def show_heatmap(gdf):
    df = gdf.copy()
    df['latitude'] = df.geometry.y
    df['longitude'] = df.geometry.x

    heatmap_layer = pdk.Layer(
        "HeatmapLayer",
        data=df[['latitude', 'longitude']],
        opacity=0.9,
        get_position=["longitude", "latitude"],
        aggregation='SUM',
    )

    view_state = pdk.ViewState(
        latitude=55.755864,
        longitude=37.617698,
        zoom=6,
        pitch=0,
        width=1200,
        height=600,
    )

    r = pdk.Deck(
        layers=[heatmap_layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v9'
    )

    st.write("## Теплокарта мероприятий:", "показаны места проведения выбранных мероприятий.")
    st.pydeck_chart(r)

filtered_gdf = filter_geodata(gdf, category, start_time)

show_heatmap(filtered_gdf)
