# Importing necessary libraries
import requests
import duckdb
import streamlit as st
import plotly.express as px
import re

# Setting Streamlit page configuration
st.set_page_config(layout="wide")

col1, col2, col3 = st.columns(3)
col2.title("2023 Wrapped for Gitcoin Donors")
col2.markdown("2023 may be over, but the imapct of your donations will continue to burst into the new year. Enter your address below to see your year in review as a Gitcoin donor!")
col2.markdown("For other wins for Gitcoin and community, check out [2023: Year in Review](https://2023.gitcoin.co/)")

# Fetching the latest IPFS CID from a specified URL
LATEST_IPFS_CID_URL = "https://raw.githubusercontent.com/davidgasquez/gitcoin-grants-data-portal/main/data/IPFS_CID"
LATEST_IPFS_CID = requests.get(LATEST_IPFS_CID_URL).text.strip()

# Constructing the gateway URL
GATEWAY_URL = f"https://ipfs.filebase.io/ipfs/{LATEST_IPFS_CID}/"

# Get the address
address = str(col2.text_input('Paste your Ethereum address here starting "0x":',help('ENS not supported, please enter 42-character hexadecimal address starting with "0x"')))

if address != 'None':
    progress_text = "Looking up! Please wait."
    my_bar = col2.progress(0, text=progress_text)
    
    if not re.match(r'^(0x)?[0-9a-f]{40}$', address, flags=re.IGNORECASE):
        col2.error('Not a valid address. Please enter a valid 42-character hexadecimal Ethereum address starting with "0x"')
        my_bar.empty()
    else:
    
        my_bar.progress(10, text='Valid address found. Searching for your contributions...:mag_right:. Hang tight!')
        # Querying the database
        QUERY = f"""
        select
            votes.voter as voter,
            round.name as round,
            strftime(to_timestamp(round_start_time),'%B %Y') as round_start,
            projects.title as project,
            round(sum(votes.amount_usd), 0) as amount
        from '{GATEWAY_URL}/round_votes.parquet' as votes,
             '{GATEWAY_URL}/rounds.parquet' as round,
             '{GATEWAY_URL}/projects.parquet' as projects
        where votes.round_id = lower(round.id)
          and votes.project_id = projects.project_id
          and voter = lower('{address}')
          and round_start_time >= 1672531200
          and round_end_time <= 1703980800
        group by votes.voter, round.name, strftime(to_timestamp(round_start_time),'%B %Y'), projects.title
        """
        query_result = duckdb.sql(QUERY).df()
    
        if query_result.empty == True:
            col2.error('Sorry, no records found for this address. Please try another address.')
            my_bar.empty()
        else:
    
            my_bar.progress(90, text='Compiling results for display...')
    
            # Processing query results
            query_result["unique_round"] = query_result["round"] + " (" + query_result["round_start"] + ")"
            project_num = query_result.project.nunique()
            total_donation = query_result['amount'].sum()
            rounds_num = query_result.unique_round.nunique()
    
            my_bar.progress(100, text='Completed!')
            my_bar.empty()
    
            msg = '## Congratulations regen! In 2023, you have contributed $' + str(total_donation) + ' to ' + str(project_num) + ' projects in ' + str(rounds_num) + ' rounds!'
            # Displaying summary statistics
            col2.markdown(msg)
    
            # Creating a sunburst chart
            fig = px.sunburst(query_result, path=['unique_round', 'project'], values='amount')
            fig.update_layout(width=1000, height=1000)
    
            bcol1, bcol2, bcol3 = st.columns(3)    
            # Displaying the sunburst chart
            bcol2.markdown("### Check out your 2023 contribution burst:")
            bcol2.markdown("*Tap on a round to drill down*")
            st.plotly_chart(fig, use_container_width=True)
    
            # Aggregating data for top rounds and projects
            rounds = query_result[['unique_round', 'amount']]
            top_rounds = rounds.groupby(['unique_round']).sum()
            projects = query_result[['project', 'amount']]
            top_projects = projects.groupby('project').sum()
    
            # Setting up Streamlit columns
            lcol1, lcol2, lcol3, lcol4 = st.columns([1,1,1,1])
    
            # Displaying top rounds
            lcol2.markdown("### Your top rounds:")
            lcol2.dataframe(top_rounds.sort_values(by="amount", ascending=False).head(5), column_config={"unique_round": st.column_config.SelectboxColumn(label='Round',width="medium"), "amount": st.column_config.NumberColumn(label='$', format='$%.0f')})
    
            # Displaying top projects
            lcol3.markdown("### Your top projects:")
            lcol3.dataframe(top_projects.sort_values(by="amount", ascending=False).head(5), column_config={"project": st.column_config.SelectboxColumn(label='Project',width="medium"),"amount": st.column_config.NumberColumn(label='$', format='$%.0f')})
    
            st.balloons()

    st.markdown("*This is one of the experiments for the project [GrantsScope](http://grantsscope.xyz/) aiming to improve the discoverability of projects and reduce information asymmetry in public goods funding. Credits to [Gitcoin Grants Data Portal](https://davidgasquez.github.io/gitcoin-data/) by [David Gasquez](https://twitter.com/davidgasquez) that serves as the data staging layer for this reporting. To report issues, ping [here](https://t.me/rohitmalekar)*")    
            
