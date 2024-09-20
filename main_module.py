# Copyright (C) 2024 Warren Usui, MIT License
"""
Scrape Wikipedia pages for information about US college teams.

This program comes from my obsession with team nicknames.   It attempts
to glean data from from collegiate sports associations.  It currently
scrapes:
    - NCAA (3 divisions)
    - NAIA

The NCCAA and NJCAA Wikipedia lists did not include nicknames, and many
of the NCCAA schools are members of the NAIA or NCAA.  Also, at the
community college level, it appears that the CCCAA and the NWAC are not
included on Wikipedia lists.  It's not clear to me what other associations
at the Junior College level may be missing.

THe USCAA schools were going to be added but there is also overlap here
with the NAIA, and some of the schools may be two year colleges.  Also,
the entire Penn State University Athletic Conference consists of the
Penn State regional Commonwealth schools and 10 of them are named
Nittany Lions, which I think will skew my nickname research.

This is a one-off program and so it ain't gonna be super elegant.
"""
import json
import requests
import pandas as pd

ASSOC = {'NCAA_Division_I_institutions': 1,
        'NCAA Division_II_institutions': 0,
        'NCAA Division_III_institutions': 0,
        'NAIA_institutions': 0}

def get_websites():
    """
    Get list of websites
    """
    return list(map(lambda a: f'https://en.wikipedia.org/wiki/List_of_{a}',
                    ASSOC))

def field_edits(field):
    """
    Remove excess text from fields
    """
    for bdata in  ['.mw-', '[']:
        if bdata in field:
            return field.split(bdata)[0]
    return field

def cleanup(clist, data_frm):
    """
    Clean columns and only display common columns
    """
    for entry in clist:
        data_frm[entry] = data_frm[entry].apply(field_edits)
    return data_frm[clist]

def rfmt_df(data_frm, assoc_indx):
    """
    Reformat the dataframes into a common set.
    """
    sthead = list(filter(lambda a: a.startswith('State'),
                      data_frm.columns.values.tolist()))[0]
    data_frm = data_frm.rename(columns={sthead: 'State'})
    data_frm = data_frm.rename(columns={'Primary': 'Conference'})
    if 'Common name' in data_frm.columns.values.tolist():
        data_frm = data_frm.rename(columns={'Common name': 'Institution'})
    else:
        data_frm = data_frm.rename(columns={'School': 'Institution'})
    data_frm['Association'] = data_frm.apply(lambda a:
            list(ASSOC.keys())[assoc_indx][0:-len('_institutions')],
            axis=1)
    data_frm['Nickname'] = data_frm['Nickname'].apply(field_edits)
    return cleanup(['Institution', 'Nickname', 'City', 'State',
                     'Conference', 'Association'], data_frm)

def gw_info(nickname):
    """
    Split up nickname text
    """
    asplit = list(map(nickname.split, [' and ', ' & ']))
    sh_info = list(filter(lambda a: len(a) == 2, asplit))
    if not sh_info:
        return [nickname, '-']
    return sh_info[0]

def fix_mw_teams(dframe):
    """
    Breakup nicknames into Men's and Women's teams
    """
    dframe['Generic Nickname'] = dframe['Nickname'].apply(
                lambda a: gw_info(a)[0])
    dframe["Women's Nickname"] = dframe['Nickname'].apply(
                lambda a: gw_info(a)[1])
    dframe = dframe.drop(columns=['Nickname'])
    return dframe

def get_schools():
    """
    Loop through schools in each association
    """
    assoc_list = []
    for url in enumerate(get_websites()):
        indx = ASSOC[url[1].split('List_of_')[-1]]
        tables = pd.read_html(requests.get(url[1], timeout=20).text)
        assoc_list.append(rfmt_df(tables[indx], url[0]))
    return fix_mw_teams(pd.concat(assoc_list)).reset_index(drop=True)

def output_school(file_name):
    """
    Wrapper that saves excel file
    """
    get_schools().to_excel(file_name)

def analyze():
    """
    Generate dict with index of words and associated rows from the
    dataframe returned by get_schools
    """
    dframe = get_schools()
    pool = list(map(lambda a: dframe.iloc[a].to_dict(),
                    list(range(len(dframe)))))
    ndict = {}
    for ndata in enumerate(pool):
        for keyword in ndata[1]['Generic Nickname'].split():
            if keyword in ndict:
                ndict[keyword].append(ndata[0])
            else:
                ndict[keyword] = [ndata[0]]
    return {'pool': pool, 'words': ndict}

def concordance():
    """
    Save word list and associated schools in dictionary.txt and
    dictionary.json
    """
    def sc_and_n(school):
        return ' '.join([data_dict['pool'][school]['Institution'],
                         data_dict['pool'][school]['Generic Nickname']])
    data_dict = analyze()
    json_out = {}
    with open('dictionary.txt', 'w', encoding='utf-8') as fdict:
        for keyword in sorted(data_dict['words']):
            print(f'{keyword}:', file=fdict)
            json_out[keyword] = []
            for school in data_dict['words'][keyword]:
                print(f'\t{sc_and_n(school)}', file=fdict)
                json_out[keyword].append(sc_and_n(school))
    with open('dictionary.json', 'w', encoding='utf-8') as jsonf:
        json.dump(json_out, jsonf, indent=4)

if __name__ == "__main__":
    concordance()
    output_school('nicknames.xlsx')
