
import pandas as pd
import pdfplumber as pf

PROVINCIAL_POSITIONS = ("PROVINCIAL GOVERNOR", "PROVINCIAL VICE-GOVERNOR", "MEMBER, SANGGUNIANG PANLALAWIGAN")

def extract_candidates_from_file(filename: str, include_senators: bool = True, include_partylists: bool = True, include_provincial: bool = True, include_barmm_partylists: bool = True):
    master_list = []
    master_dict = {}
    temp_partylists = []
    temp_bangsamoro = []

    # read file
    try:
        with pf.open(filename) as pdf:
            print(len(pdf.pages))
            if len(pdf.pages) != 2 and len(pdf.pages) != 4:
                raise Exception("Error dealing with this LGU")
            
            for i in range(2):
                page = pdf.pages[i]
                tables = page.find_tables()
                if i == 0:
                    # deal with senators and local candidates
                    for table in tables:
                        master_list = [*master_list, *table.extract()]
                else:
                    # deal with temp_partylists
                    # tables = page.find_tables()
                    for table in tables:
                        temp_partylists = [*temp_partylists, *table.extract()]
            
            # factor in BANGSAMORO
            if len(pdf.pages) == 4:
                page = pdf.pages[2]
                tables = page.find_tables()

                for table in tables:
                    temp_bangsamoro = [*temp_bangsamoro, *table.extract()]
                print(temp_bangsamoro)
    except:
        # catch non-existent file error
        return None

    # treat first page (senators and local positions)
    curr_pos = None
    for i in range(len(master_list)):
        row = master_list[i]

        if row[0].startswith("SENATOR"):
            curr_pos = "SENATOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("MEMBER, HOUSE OF REPRESENTATIVES"):
            curr_pos = "MEMBER, HOUSE OF REPRESENTATIVES"
            master_dict[curr_pos] = []
        elif row[0].startswith("PROVINCIAL GOVERNOR"):
            curr_pos = "PROVINCIAL GOVERNOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("PROVINCIAL VICE-GOVERNOR"):
            curr_pos = "PROVINCIAL VICE-GOVERNOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("MEMBER, SANGGUNIANG PANLALAWIGAN"):
            curr_pos = "MEMBER, SANGGUNIANG PANLALAWIGAN"
            
            # get max number of councilors to vote for
            strNum = row[0].split("\n")[0].split(" ")[-1]
            try:
                master_dict["maxProvincialBoardSlots"] = int(strNum)
            except:
                return None
            
            master_dict[curr_pos] = []
        elif row[0].startswith("MAYOR"):
            curr_pos = "MAYOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("VICE-MAYOR"):
            curr_pos = "VICE-MAYOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("MEMBER, SANGGUNIANG BAYAN"):
            curr_pos = "MEMBER, SANGGUNIANG BAYAN"
            # get max number of councilors to vote for
            strNum = row[0].split("\n")[0].split(" ")[-1]
            try:
                master_dict["maxCouncilorBoardSlots"] = int(strNum)
            except:
                return None
            
            master_dict[curr_pos] = []
        # add support for BANGSAMORO
        else:
            # deal with actually adding data
            if include_senators == False and curr_pos == "SENATOR":
                continue
            if include_provincial == False and curr_pos in PROVINCIAL_POSITIONS:
                continue
            
            for candidate in row:
                splitted_candidate = candidate.split(" ")
                ballot_number = splitted_candidate.pop(0).removesuffix(".")  # pop the ballot number, leaving only the ballot number
                ballot_name = " ".join(splitted_candidate)
                
                master_dict[curr_pos].append((ballot_number, ballot_name.replace("\n", " ")))
    
    # treat second page (temp_partylists)
    partylists = []

    if include_partylists:
        for i in range(5):
            for j in range(1,39):   # ignore the first row
                try:
                    entry:str = temp_partylists[j][i]

                    splitted_entry = entry.split(" ")
                    ballot_number = splitted_entry.pop(0)   # pop the ballot number, leaving only the name
                    ballot_name = " ".join(splitted_entry)

                    partylists.append((ballot_number, ballot_name.replace("\n", " ")))
                except:
                    continue

        master_dict["PARTYLIST"] = partylists

    # short-circuit when not a bangsamoro province
    if len(temp_bangsamoro) == 0:
        return master_dict

    # handle bangsamoro candidates
    curr_pos = None
    for i in range(len(temp_bangsamoro)):
        row = temp_bangsamoro[i]

        if row[0].startswith("BARMM PARTY REPRESENTATIVES"):
            curr_pos = "BARMM PARTY REPRESENTATIVES"
            master_dict[curr_pos] = []
        elif row[0].startswith("BARMM MEMBERS OF THE PARLIAMENT"):
            curr_pos = "BARMM MEMBERS OF THE PARLIAMENT"
            master_dict[curr_pos] = []
        else:
            if include_barmm_partylists == False and curr_pos == "BARMM PARTY REPRESENTATIVES":
                continue
            
            for candidate in row:
                splitted_candidate = candidate.split(" ")
                ballot_number = splitted_candidate.pop(0).removesuffix(".")  # pop the ballot number, leaving only the ballot number
                ballot_name = " ".join(splitted_candidate)
                
                master_dict[curr_pos].append((ballot_number, ballot_name.replace("\n", " ")))

    return master_dict

sample_typical = "BADOC.pdf"
sample_barmm = "HADJI_MOHAMMAD_AJUL.pdf"

extract_candidates_from_file(f"temp/{sample_typical}")
extract_candidates_from_file(f"temp/{sample_barmm}")