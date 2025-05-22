import pandas as pd
import streamlit as st
import plotly.express as px
from streamlit_option_menu import option_menu

# --- Streamlit Page Setup ---
st.set_page_config(page_title="Network Dashboard", layout="wide")

# --- Sidebar Tabs Using streamlit-option-menu ---
with st.sidebar:
    selected_tab = option_menu(
        menu_title="📁 Navigation",
        options=["Deployment Config", "Service Type Cell Wise", "Service Type->Cell Mapping", "Trends"],
        icons=["bar-chart", "line-chart"],
        menu_icon="cast",
        default_index=0,
        orientation="vertical"
    )

# --- Main Title ---
st.title("📊 Network Service Dashboard")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])

if uploaded_file:
    # Load data
    df = pd.read_excel(uploaded_file)

    # --- Validate and Parse Required Columns ---
    required_columns = ['Time of Access', 'Service Type', 'Cell_id']
    for col in required_columns:
        if col not in df.columns:
            st.error(f"❌ Required column '{col}' is missing from the uploaded file.")
            st.stop()

    # Parse 'Time of Access' to datetime.time
    try:
        df['Time of Access'] = pd.to_datetime(df['Time of Access'].astype(str), format='%H:%M:%S').dt.time
    except:
        st.error("❌ 'Time of Access' column must be in HH:MM:SS format")
        st.stop()

    # Combine 'Date' and 'Time of Access' into a datetime column
    if 'Date' in df.columns:
        df['Access Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time of Access'].astype(str))
    else:
        st.error("❌ The file must include a 'Date' column to enable time filtering.")
        st.stop()

    # --- Show Metrics ---
    st.markdown("### 📌 Quick Stats")
    colA, colB, colC = st.columns(3)
    colA.metric("Total Records", len(df))
    colB.metric("Unique Service Types", df['Service Type'].nunique())
    colC.metric("Unique Cells", df['Cell_id'].nunique())

    with st.expander("🔍 Preview Uploaded Data"):
        st.dataframe(df.head())

    # --- Service Type Cell Wise ---
    if selected_tab == "Service Type Cell Wise":
        col1, col2, col3 = st.columns(3)
        chart_type = col1.selectbox("Chart Type", ["Bar Chart", "Pie Chart"])
        cell_option = col2.selectbox("Select Cell", ["All Cells"] + sorted(df['Cell_id'].dropna().astype(int).astype(str).unique()))
        time_range = col3.selectbox("Time Range",
                                    ["Last 15 Minutes", "Last 30 Minutes", "Last 5 Hours", "Last 12 Hours",
                                     "Last 24 Hours"])

        # ✅ Parse the date and time correctly based on your format
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%m-%Y')
        df['Time of Access'] = pd.to_datetime(df['Time of Access'], format='%H:%M:%S').dt.time

        # ✅ Combine into full timestamp
        df['Access_Timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time of Access'].astype(str))

        # Filter based on cell selection
        filtered_df = df.copy()
        if cell_option != "All Cells":
            filtered_df = filtered_df[filtered_df['Cell_id'].astype(str) == cell_option]

        # Time range filtering
        now = filtered_df['Access_Timestamp'].max()
        time_deltas = {
            "Last 15 Minutes": pd.Timedelta(minutes=15),
            "Last 30 Minutes": pd.Timedelta(minutes=30),
            "Last 5 Hours": pd.Timedelta(hours=5),
            "Last 12 Hours": pd.Timedelta(hours=12),
            "Last 24 Hours": pd.Timedelta(hours=24)
        }

        filtered_df = filtered_df[filtered_df['Access_Timestamp'] >= now - time_deltas[time_range]]

        if filtered_df.empty:
            st.warning("No data available for the selected filters.")
        else:
            service_counts = filtered_df['Service Type'].value_counts().reset_index()
            service_counts.columns = ['Service Type', 'Count']

            st.subheader(f"📍 Service Type Distribution - {time_range}")
            if chart_type == "Pie Chart":
                if len(service_counts) > 10:
                    top_services = service_counts.nlargest(10, 'Count')
                    others = service_counts.iloc[10:]['Count'].sum()
                    others_row = pd.DataFrame([{'Service Type': 'Others', 'Count': others}])
                    top_services = pd.concat([top_services, others_row], ignore_index=True)
                else:
                    top_services = service_counts
                fig = px.pie(top_services, names='Service Type', values='Count', title='Top 10 Service Types')
            else:
                service_counts = service_counts.sort_values(by="Count", ascending=False)
                fig = px.bar(service_counts, x='Service Type', y='Count', title='Service Usage by Type')

            st.plotly_chart(fig, use_container_width=True)


    # --- Trends ---
    elif selected_tab == "Trends":
        trend_range = st.selectbox("Select Time Range", ["Last Day", "Last Week", "Last 5 Hours"])

        trend_df = df.copy()

        # ✅ Parse the columns properly
        trend_df['Date'] = pd.to_datetime(trend_df['Date'], format='%d-%m-%Y')
        trend_df['Time of Access'] = pd.to_datetime(trend_df['Time of Access'], format='%H:%M:%S').dt.time

        # ✅ Combine into full datetime
        trend_df['Access Datetime'] = pd.to_datetime(
            trend_df['Date'].astype(str) + ' ' + trend_df['Time of Access'].astype(str))

        now = trend_df['Access Datetime'].max()

        if trend_range == "Last Day":
            trend_df = trend_df[trend_df['Access Datetime'] >= now - pd.Timedelta(days=1)]
        elif trend_range == "Last Week":
            trend_df = trend_df[trend_df['Access Datetime'] >= now - pd.Timedelta(weeks=1)]
        elif trend_range == "Last 5 Hours":
            trend_df = trend_df[trend_df['Access Datetime'] >= now - pd.Timedelta(hours=5)]

        # ⏱️ Grouping data into 30-minute bins
        trend_df['Time Group'] = trend_df['Access Datetime'].dt.floor('30min')
        trend_counts = trend_df.groupby(['Time Group', 'Service Type']).size().reset_index(name='User Count')

        st.subheader("📈 User Trends Over Time")
        fig2 = px.line(trend_counts, x='Time Group', y='User Count', color='Service Type',
                       title='Users per Service Type Over Time')
        st.plotly_chart(fig2, use_container_width=True)


    elif selected_tab == "Deployment Config":

        st.subheader("🛠️ Deployment Configuration Summary")

        # Required columns check

        required_deploy_cols = ['Service Type', 'Latency (ms)', 'Bandwidth', 'Slice ID' ,'Slice Type']

        for col in required_deploy_cols:

            if col not in df.columns:
                st.error(f"❌ Required column '{col}' is missing.")

                st.stop()

        # Group data by Service Type

        grouped = df.groupby(['Service Type'])

        summary_data = []

        for service, group in grouped:
            max_latency = group['Latency (ms)'].max()

            bandwidth = group['Bandwidth'].iloc[0]

            slice_id = int(group['Slice ID'].iloc[0])

            slice_type = group['Slice Type'].iloc[0]

            user_count = len(group)

            summary_data.append({

                'Slice ID': slice_id,

                'Slice Type': slice_type,

                'Service Type': service,

                'Latency': f"<= {max_latency:.2f} ms",

                'Bandwidth': bandwidth,

                'Number of users': user_count

            })

        summary_df = pd.DataFrame(summary_data)


        # Style function to bold first row

        def highlight_first_row(row):

            return ['font-weight: bold' if row.name == 0 else '' for _ in row]


        # Apply styling: bold header with dark blue background + bold first row

        styled_df = summary_df.style.apply(highlight_first_row, axis=1) \
 \
            .set_table_styles([

            {

                'selector': 'th',

                'props': [

                    ('font-weight', 'bold'),

                    ('background-color', '#003366'),

                    ('color', 'white'),

                    ('text-align', 'center')

                ]

            }

        ])

        st.write(styled_df)

else:
    st.info("📥 Please upload an Excel file to get started.")
