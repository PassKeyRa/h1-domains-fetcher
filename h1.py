import requests
import json
import argparse

graphql = "https://hackerone.com/graphql"

programs_query = '''query DirectoryQuery(
  $cursor: String
  $first: Int
  $where: FiltersTeamFilterInput
) {
  teams(
    first: $first
    after: $cursor
    where: $where
  ) {
    pageInfo {
      endCursor
      hasNextPage
      __typename
    }
    edges {
      node {
        handle
      }
    }
  }
}'''

program_query = '''query TeamAssets($handle: String!) {
  team(handle: $handle) {
    handle
    in_scope_assets: structured_scopes(
      first: 1000
      archived: false
      eligible_for_submission: true
    ) {
      edges {
        node {
          asset_type
          asset_identifier
          max_severity
          eligible_for_bounty
        }
      }
    }
  }
}'''

where_programs = {
                    "submission_state": {"_eq": "open"}
                 }

def get_programs_handles():
    handles = []
    s = requests.Session()
    hasNextPage = True
    first = 100
    cursor = ""
    while hasNextPage:
        r = s.post(graphql, json={'variables':{"first":first, "cursor":cursor, "where": where_programs},'query':programs_query}, headers={'Content-Type':'application/json'})
        try:
            teams = r.json()['data']['teams']
        except KeyError:
            error = r.json()['errors']
            print(f"Some errors occured: {error}")
            exit(1)
        hasNextPage = teams['pageInfo']['hasNextPage']
        cursor = teams['pageInfo']['endCursor']
        for edge in teams['edges']:
            handles.append(edge['node']['handle'])
        print(f'{len(handles)} programs')
        if hasNextPage:
            print('Fetching next')
    return handles

def get_scope(handles, eligible_only=False):
    urls = []
    s = requests.Session()
    for h in handles:
        r = s.post(graphql, json={'variables':{'handle':h},'query':program_query}, headers={'Content-Type':'application/json'})
        try:
            in_scope = r.json()['data']['team']['in_scope_assets']['edges']
        except KeyError:
            error = r.json()['errors']
            print(f"some errors occured: {error}")
            exit(1)
        for edge in in_scope:
            if eligible_only and not edge['node']['eligible_for_bounty']:
                    continue
            if edge['node']['asset_type'] not in ['URL']:
                continue
            url = edge['node']['asset_identifier']
            if 'http' in url:
                url = url.split('://')[1]
            url = url.split('/')[0]
            urls.append(url)
        print(f'{len(urls)} urls')
    return urls

def main():
    parser = argparse.ArgumentParser(description='HackerOne domains fetcher')
    parser.add_argument('--eligible', action='store_true', help='Fetch eligible only domains')
    parser.add_argument('file', help='File to save domains')
    args = parser.parse_args()
    handles = get_programs_handles()
    urls = get_scope(handles, eligible_only=args.eligible)

    with open(args.file, 'w') as f:
        f.write('\n'.join(urls))

    print('Done')

if __name__ == '__main__':
    main()
