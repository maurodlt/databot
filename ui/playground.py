import queue
import streamlit as st
import streamlit_antd_components as sac

from app.bot.library.session_keys import FILTERS
from schema.field_type import BOOLEAN, DATETIME, NUMERIC, TEXTUAL
from schema.filter import Filter, boolean_operators, datetime_operators, numeric_operators, textual_operators
from ui.bot_container import bot_container
from app.app import get_app
from ui.utils.session_state_keys import HISTORY, PLOTS, PLOT_INDEX, PROJECTS, QUEUE, SELECTED_PROJECT, SESSION_ID, \
    TABLES, TABLE_INDEX
from ui.sidebar import project_selection
from ui.utils.utils import get_page_height

BOT_CONTAINER_WIDTH = 0.3


def playground():
    """Show the playground container"""
    app = get_app()
    with st.sidebar:
        project_selection()

    if PROJECTS not in st.session_state:
        st.session_state[PROJECTS] = {}
    if SELECTED_PROJECT not in st.session_state and app.projects:
        st.session_state[SELECTED_PROJECT] = app.projects[0]

    project = st.session_state[SELECTED_PROJECT] if SELECTED_PROJECT in st.session_state else None

    if project and project.name not in st.session_state[PROJECTS]:
        st.session_state[PROJECTS][project.name] = {
            SESSION_ID: None,
            HISTORY: [],
            QUEUE: queue.Queue(),
            PLOTS: [],
            PLOT_INDEX: None,
            TABLES: [],
            TABLE_INDEX: None
        }

    st.markdown("<h1 style='text-align: center;'>BESSER Conversational Data Analysis</h1>", unsafe_allow_html=True)
    bot_col, dash_col = st.columns([BOT_CONTAINER_WIDTH, 1 - BOT_CONTAINER_WIDTH])

    with bot_col:
        st.subheader(f"🤖 DataBot")
        bot_container()
    with dash_col:
        # TODO: SPECIFIC METHOD FOR DASHBOARD, LIKE bot_container()
        if project:
            selected_tab = sac.tabs([
                sac.TabsItem(label='Data', icon='database-fill'),
                sac.TabsItem(label='Plots', icon='bar-chart-fill'),
                sac.TabsItem(label='Filters', icon='funnel-fill'),
                sac.TabsItem(label='Settings', icon='gear-fill'),
            ], format_func='title', align='center', return_index=True, grow=True)
            if selected_tab == 0:  # Data
                if not st.session_state[PROJECTS][project.name][TABLES]:
                    st.dataframe(project.df, height=get_page_height(235), use_container_width=True)
                else:
                    # st.write(st.session_state[PROJECTS][project.name][TABLES][TABLE_INDEX])
                    table_container = st.container()
                    navigate_dashboard_elements(TABLES, TABLE_INDEX)
                    table_index = st.session_state[PROJECTS][project.name][TABLE_INDEX]
                    table_container.dataframe(st.session_state[PROJECTS][project.name][TABLES][table_index], height=get_page_height(235), use_container_width=True)
            elif selected_tab == 1:  # Plots
                if not st.session_state[PROJECTS][project.name][PLOTS]:
                    st.info(
                        'Here you can view some graphical answers generated by the bot, like line charts or histograms.',
                        icon='💡'
                    )
                else:
                    plot_container = st.container()
                    navigate_dashboard_elements(PLOTS, PLOT_INDEX)
                    plot_index = st.session_state[PROJECTS][project.name][PLOT_INDEX]
                    plot_container.plotly_chart(st.session_state[PROJECTS][project.name][PLOTS][plot_index], use_container_width=True)
            elif selected_tab == 2:  # Filters
                if not project.bot_running:
                    st.info(
                        'Run the bot to be able to apply filters to the data.',
                        icon='💡'
                    )
                else:
                    field_col, operator_col, value_col = st.columns(3)
                    with field_col:
                        field_readable_name = st.selectbox(
                            label='Select a field',
                            label_visibility='visible',
                            options=[field_schema.readable_name for field_schema in project.data_schema.field_schemas],
                            index=None
                        )
                        target_field_schema = None
                        for field_schema in project.data_schema.field_schemas:
                            if field_schema.readable_name == field_readable_name:
                                target_field_schema = field_schema
                                break
                    with operator_col:
                        target_operators = []
                        if target_field_schema:
                            if target_field_schema.type.t == NUMERIC:
                                target_operators = numeric_operators
                            elif target_field_schema.type.t == TEXTUAL:
                                target_operators = textual_operators
                            elif target_field_schema.type.t == DATETIME:
                                target_operators = datetime_operators
                            elif target_field_schema.type.t == BOOLEAN:
                                target_operators = boolean_operators
                        filter_operator = st.selectbox(
                            label='Select an operator',
                            label_visibility='visible',
                            options=target_operators,
                            index=0
                        )
                    filter_value_ok = True
                    with value_col:
                        if filter_operator:
                            if target_field_schema.type.t == NUMERIC:
                                filter_value = st.number_input('Choose a NUMBER', value=None, format='%f')
                            elif target_field_schema.type.t == TEXTUAL:
                                filter_value = st.text_input('Choose a value')
                            elif target_field_schema.type.t == DATETIME:
                                if filter_operator == 'between':
                                    date_interval = st.date_input('Choose a date', value=[], format='DD/MM/YYYY')
                                    time0 = st.time_input('Starting time', value=None, step=60)
                                    time1 = st.time_input('Ending time', value=None, step=60)
                                    if len(date_interval) == 2:
                                        filter_value = [(date_interval[0], time0), (date_interval[1], time1)]
                                    else:
                                        filter_value = [(None, time0), (None, time1)]
                                    if (len(date_interval) == 1) or (time0 and not time1) or (not time0 and time1) or time0 > time1:
                                        st.error('Set a proper date interval, time interval or both')
                                        filter_value_ok = False
                                else:
                                    date = st.date_input('Choose a date', value=None, format='DD/MM/YYYY')
                                    time = st.time_input('Choose a time', value=None, step=60)
                                    filter_value = [(date, time)]
                            elif target_field_schema.type.t == BOOLEAN:
                                filter_value = st.selectbox('Choose a value', options=[True, False], index=0)
                        else:
                            st.text_input('Select a value', disabled=True, placeholder='No operator selected')

                    session_id = st.session_state[PROJECTS][project.name][SESSION_ID]
                    if session_id and project.databot.bot.get_session(session_id):
                        bot_filters: list = project.databot.bot.get_session(session_id).get(FILTERS)
                        if st.button(
                                label='Apply filter',
                                disabled=not (target_field_schema and filter_operator and filter_value_ok),
                                use_container_width=False,
                                type='primary'
                        ):
                            bot_filter: Filter = Filter(target_field_schema, filter_operator, filter_value)
                            if bot_filter not in bot_filters:
                                bot_filters.append(bot_filter)
                            else:
                                st.error('This filter already exists.')
                        with st.expander('All filters', expanded=True):
                            if bot_filters:
                                delete_filters = []
                                for bot_filter in bot_filters:
                                    selected = st.checkbox(f'{bot_filter.field.readable_name} {bot_filter.operator} {bot_filter.value}')
                                    if selected:
                                        delete_filters.append(bot_filter)
                                if st.button(label='Delete', key='delete_field_synonym'):
                                    for delete_filter in delete_filters:
                                        bot_filters.remove(delete_filter)
                                    st.rerun()
                            else:
                                st.error('There are no filters')
            elif selected_tab == 3:  # Project settings
                def reset_chat():
                    session_id = st.session_state[PROJECTS][project.name][SESSION_ID]
                    project.databot.bot.get_session(session_id).set(FILTERS, [])
                    st.session_state[PROJECTS][project.name][HISTORY] = []
                    st.session_state[PROJECTS][project.name][PLOTS] = []
                    st.session_state[PROJECTS][project.name][PLOT_INDEX] = None
                    st.session_state[PROJECTS][project.name][TABLES] = []
                    st.session_state[PROJECTS][project.name][TABLE_INDEX] = None
                    project.databot.bot.reset(session_id)
                st.button(label='Reset chat', on_click=reset_chat)

        else:
            st.info(
                'Here is the dashboard where you can visualize the answers generated by the bot.',
                icon='💡'
            )


def navigate_dashboard_elements(elements_label, index_label):
    project = st.session_state[SELECTED_PROJECT]
    previous_index = st.session_state[PROJECTS][project.name][index_label]
    selected_button = sac.buttons([
        sac.ButtonsItem(icon='chevron-bar-left'),
        sac.ButtonsItem(icon='caret-left-fill'),
        sac.ButtonsItem(label=f'{st.session_state[PROJECTS][project.name][index_label] + 1} / {len(st.session_state[PROJECTS][project.name][elements_label])}'),
        sac.ButtonsItem(icon='caret-right-fill'),
        sac.ButtonsItem(icon='chevron-bar-right'),
        sac.ButtonsItem(label='Delete this element'),
    ], align='center', shape='circle', index=None, type='text', return_index=True)

    if selected_button == 0:  # Move to the top left
        st.session_state[PROJECTS][project.name][index_label] = 0
        if previous_index > 0:
            st.rerun()
    elif selected_button == 1:  # Move to the left
        st.session_state[PROJECTS][project.name][index_label] = max(0, st.session_state[PROJECTS][project.name][index_label] - 1)
        if previous_index > 0:
            st.rerun()
    elif selected_button == 3:  # Move to the right
        st.session_state[PROJECTS][project.name][index_label] = min(
            st.session_state[PROJECTS][project.name][index_label] + 1,
            len(st.session_state[PROJECTS][project.name][elements_label]) - 1
        )
        if previous_index < len(st.session_state[PROJECTS][project.name][elements_label]) - 1:
            st.rerun()
    elif selected_button == 4:  # Move to the top right
        st.session_state[PROJECTS][project.name][index_label] = len(st.session_state[PROJECTS][project.name][elements_label]) - 1
        if previous_index < len(st.session_state[PROJECTS][project.name][elements_label]) - 1:
            st.rerun()
    elif selected_button == 5:  # Delete element
        del st.session_state[PROJECTS][project.name][elements_label][previous_index]
        if previous_index >= len(st.session_state[PROJECTS][project.name][elements_label]):
            st.session_state[PROJECTS][project.name][index_label] -= 1
        st.rerun()
