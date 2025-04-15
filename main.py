
import pandas as pd
import pdfplumber as pf

PROVINCIAL_POSITIONS = ("PROVINCIAL GOVERNOR", "PROVINCIAL VICE-GOVERNOR", "MEMBER, SANGGUNIANG PANLALAWIGAN")

def extract_candidates_from_file(filename: str, include_senators: bool = True, include_partylists: bool = True, include_provincial: bool = True):
    master_list = []
    master_dict = {}
    temp_partylists = []

    # read file
    try:
        with pf.open(filename) as pdf:
            if len(pdf.pages) != 2:
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
            master_dict[curr_pos] = []
        elif row[0].startswith("MAYOR"):
            curr_pos = "MAYOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("VICE-MAYOR"):
            curr_pos = "VICE-MAYOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("MEMBER, SANGGUNIANG BAYAN"):
            curr_pos = "MEMBER, SANGGUNIANG BAYAN"
            master_dict[curr_pos] = []
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

        partylists = pd.DataFrame(partylists)
        print(pd.DataFrame(master_dict["SENATOR"]))
    return (pd.DataFrame(partylists, columns=["ballot_number", "ballot_name"]))

extract_candidates_from_file("temp/BADOC.pdf", "BADOC, ILOCOS NORTE")