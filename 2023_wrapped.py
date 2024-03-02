# Importing necessary libraries
import requests
import duckdb
import streamlit as st
import plotly.express as px
import re

# Set Streamlit page configuration for layout
st.set_page_config(layout='wide')

# Streamlit page setup
col1, col2, col3 = st.columns(3)
col2.title('2023 Wrapped for Gitcoin Donors')
col2.markdown('2023 may be over, but the impact of your donations will continue to burst into the new year. '
              'Enter your address below to see your year in review as a Gitcoin donor!')
col2.markdown('For other wins for Gitcoin and community, check out [2023: Year in Review](https://2023.gitcoin.co/). To report issues, ping on Telegram [here](https://t.me/rohitmalekar).')

# Fetch the latest IPFS CID from a specified URL
#LATEST_IPFS_CID_URL = 'https://raw.githubusercontent.com/davidgasquez/gitcoin-grants-data-portal/main/data/IPFS_CID'
#LATEST_IPFS_CID = requests.get(LATEST_IPFS_CID_URL).text.strip()

# Construct the gateway URL
#GATEWAY_URL = f'https://ipfs.filebase.io/ipfs/{LATEST_IPFS_CID}/'
GATEWAY_URL = "https://k51qzi5uqu5dhn3p5xdkp8n6azd4l1mma5zujinkeewhvuh5oq4qvt7etk9tvc.ipns.cf-ipfs.com/data"

# Get the Ethereum address from user input
address = col2.text_input('Paste your Ethereum address here starting "0x":', 
                          help='ENS not supported, please enter 42-character hexadecimal address starting with "0x"')

# Process if a valid address is entered
if address != 'None':
    # Display progress bar
    progress_text = 'Looking up! Please wait.'
    my_bar = col2.progress(0, text=progress_text)
    
    # Check for valid Ethereum address
    if not re.match(r'^(0x)?[0-9a-f]{40}$', address, flags=re.IGNORECASE):
        col2.error('Not a valid address. Please enter a valid 42-character hexadecimal Ethereum address starting with "0x"')
        my_bar.empty()
    else:
        my_bar.progress(10, text='Valid address found. Searching for your contributions...:mag_right:. Hang tight!')
        
        # Database querying
        QUERY = f"""
            SELECT
                votes.donor_address AS voter,
                rounds.round_metadata_name AS round,
                strftime('%B %Y', CAST(donations_start_time AS TIMESTAMP)) AS round_start,
                projects.title AS project,
                any_value(projects.project_twitter) AS project_twitter,
                round(sum(votes.amount_in_usd), 0) AS amount
            FROM '{GATEWAY_URL}/allo_donations.parquet' AS votes,
                 '{GATEWAY_URL}/allo_rounds.parquet' AS rounds,
                 '{GATEWAY_URL}/allo_projects.parquet' AS projects
            WHERE votes.round_id = rounds.id
              AND votes.project_id = projects.id
              AND strftime('%Y', CAST(donations_start_time AS TIMESTAMP)) = '2023'
            GROUP BY votes.donor_address, rounds.round_metadata_name, strftime('%B %Y', CAST(donations_start_time AS TIMESTAMP)), projects.title        
            """

        # All results for 2023
        query_all_result = duckdb.sql(QUERY).df()

        # All results for the voter for 2023
        query_result = query_all_result.query(f"voter == '{address.lower()}'")
    
        # Process query results
        if query_result.empty:
            col2.error('Sorry, no records found for this address. Please try another address.')
            my_bar.empty()
        else:
            my_bar.progress(90, text='Compiling results for display...')
    
            # Append round name with round start (month and year) to distinguish recurring program rounds
            query_result['unique_round'] = query_result['round'] + ' (' + query_result['round_start'] + ')'
            
            # Statistics on unique number of projects, total donations, number of rounds supported    
            project_num = query_result['project'].nunique()
            total_donation = query_result['amount'].sum()
            rounds_num = query_result['unique_round'].nunique()
    
            my_bar.progress(100, text='Completed!')
            my_bar.empty()
    
            # Display summary statistics
            msg = f'## Congratulations! In 2023, you have contributed ${total_donation} to {project_num} projects in {rounds_num} rounds!'
            col2.markdown(msg)
    
            # Create and display a sunburst chart
            fig = px.sunburst(query_result, path=['unique_round', 'project'], values='amount')
            fig.update_layout(width=1000, height=1000)
    
            bcol1, bcol2, bcol3 = st.columns(3)
            bcol2.markdown('### Check out your 2023 contribution burst:')
            bcol2.markdown('*Tap on a round to drill down*')
            st.plotly_chart(fig, use_container_width=True)
    
            # Aggregate data for top rounds and projects
            rounds = query_result[['unique_round', 'amount']]
            rounds_of_voter = rounds.groupby(['unique_round']).sum()
            projects = query_result[['project', 'amount']]
            projects_of_voter = projects.groupby(['project']).sum()
    
            # Display top rounds and projects
            lcol1, lcol2, lcol3, lcol4 = st.columns([1, 1, 1, 1])
            lcol2.markdown('### Your top rounds:')
            lcol2.dataframe(rounds_of_voter.sort_values(by="amount", ascending=False).head(5), column_config={"unique_round": st.column_config.SelectboxColumn(label='Round',width="medium"), "amount": st.column_config.NumberColumn(label='$', format='$%.0f')})

            lcol3.markdown('### Your top projects:')
            lcol3.dataframe(projects_of_voter.sort_values(by="amount", ascending=False).head(5), column_config={"project": st.column_config.SelectboxColumn(label='Project',width="medium"),"amount": st.column_config.NumberColumn(label='$', format='$%.0f')})
    
            st.balloons()

            # Display personalized recommendations for 2024

            bot_col1, bot_bcol2, bot_bcol3 = st.columns(3)

            bot_bcol2.divider()
            bot_bcol2.markdown('## 2024 Recommendations')
            
            # Processing for recommendations
            # Step 1: Find top 5 projects supported by the voter
            top_projects_of_voter = projects_of_voter.sort_values(by='amount', ascending=False).head(5).reset_index()
            top_projects_of_voter_list = top_projects_of_voter['project'].tolist()    

            # Step 2: Find all other voters who also supported the top projects of this voter    
            voter_cluster = query_all_result[query_all_result['project'].isin(top_projects_of_voter_list)]
            voter_cluster_list = voter_cluster['voter'].unique().tolist()

            bot_bcol2.markdown("We looked at contributions of voters who support some of your most favorite projects to find out what else they contribute to that you don't. May be you know about these projects, may be you don't - we just thought you might like a sneak peek at this list as we gear up for Gitcoin Grants for 2024.")    
            bot_bcol2.markdown(f'A total of {len(voter_cluster_list)} unique voters also supported the top 5 projects you contributed to in 2023.')    

            # Step 3: Find all other projects supported by this voter cluster to base recommendations off of based on (a) contribution amount (b) number of votes
            projects_of_voter = projects_of_voter.reset_index()
            projects_of_cluster = query_all_result[query_all_result['voter'].isin(voter_cluster_list) & ~query_all_result['project'].isin(projects_of_voter['project'].tolist())]

            top_projects_of_cluster_amount = projects_of_cluster[['project', 'project_twitter', 'amount']].groupby(['project', 'project_twitter']).sum()
            top_projects_of_cluster_vote = projects_of_cluster[['project', 'project_twitter', 'amount']].groupby(['project', 'project_twitter']).count()

            top_projects_of_cluster_amount = top_projects_of_cluster_amount.reset_index()
            top_projects_of_cluster_amount['project_twitter'] = 'https://twitter.com/' + top_projects_of_cluster_amount['project_twitter'].astype(str)
            top_projects_of_cluster_vote = top_projects_of_cluster_vote.reset_index()
            top_projects_of_cluster_vote['project_twitter'] = 'https://twitter.com/' + top_projects_of_cluster_vote['project_twitter'].astype(str)

            # bot_bcol2.markdown(f'These voters also contributed to {top_projects_of_cluster_amount["project"].nunique()} other projects that you did not vote for.')

            bot_bcol2.markdown('Here are the top projects these voters supported that you may be interested in for your contributions in 2024:')

            bot_bcol2.markdown('### Sorted by contribution amount:')
            bot_bcol2.caption('The following projects received the most donations from voters who also supported the top 5 projects you contributed to in 2023.')
            bot_bcol2.dataframe(top_projects_of_cluster_amount.sort_values(by='amount', ascending=False).head(10),hide_index=True , column_order=("project","project_twitter"), column_config={"project": st.column_config.SelectboxColumn(label='Project',width="medium"),"project_twitter": st.column_config.LinkColumn(label='Twitter') })

            bot_bcol2.markdown('### Sorted by number of votes:')
            bot_bcol2.caption('The following projects received the most number of votes from voters who also supported the top 5 projects you contribute to in 2023.')
            bot_bcol2.dataframe(top_projects_of_cluster_vote.sort_values(by='amount', ascending=False).head(10), hide_index=True , column_order=("project","project_twitter"), column_config={"project": st.column_config.SelectboxColumn(label='Project',width="medium"),"project_twitter": st.column_config.LinkColumn(label='Twitter') })

            bot_bcol2.divider()
            bot_bcol2.markdown('If you like what you see here, contribute to **Gitcoin Grants Data Portal** and **GrantsScope** next time you see these projects on Gitcoin.')
            bot_bcol2.markdown('*This is one of the experiments for the project [GrantsScope](http://grantsscope.xyz/) aiming to improve the discoverability of projects and reduce information asymmetry in public goods funding. Credits to [Gitcoin Grants Data Portal](https://davidgasquez.github.io/gitcoin-data/) by [David Gasquez](https://twitter.com/davidgasquez) that serves as the data staging layer for this reporting.*')
