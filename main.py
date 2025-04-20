
import pandas as pd
import pdfplumber as pf
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from dotenv import load_dotenv
import psycopg as pg

load_dotenv()

db_key = os.getenv("DB_KEY")

PROVINCIAL_POSITIONS = ("PROVINCIAL GOVERNOR", "PROVINCIAL VICE-GOVERNOR")
LOCAL_POSITIONS = ("MAYOR", "VICE-MAYOR", "LGU_COUNCIL", "MEMBER, HOUSE OF REPRESENTATIVES")

download_path = os.getcwd() + "/temp"
options = webdriver.ChromeOptions()
options.add_experimental_option("prefs", {
    "download.default_directory": download_path,
    'profile.default_content_setting_values.automatic_downloads': 1
})
driver = webdriver.Chrome(options=options)

def extract_candidates_from_file(filename: str, include_senators: bool = True, include_partylists: bool = True, include_provincial: bool = True, include_barmm_partylists: bool = True, include_local:bool = True):
    master_list = []
    master_dict = {}
    temp_partylists = []
    temp_bangsamoro = []
    candidates = []
    max_provincial_board_slots = 0
    max_councilor_board_slots = 0

    # read file
    try:
        with pf.open(filename) as pdf:
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
                    for table in tables:
                        temp_partylists = [*temp_partylists, *table.extract()]
            
            # factor in BANGSAMORO
            if len(pdf.pages) == 4:
                page = pdf.pages[2]
                tables = page.find_tables()

                for table in tables:
                    temp_bangsamoro = [*temp_bangsamoro, *table.extract()]
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
                # master_dict["maxProvincialBoardSlots"] = int(strNum)
                max_provincial_board_slots = int(strNum)
            except:
                return None
            
            master_dict[curr_pos] = []
        elif row[0].startswith("MAYOR"):
            curr_pos = "MAYOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("VICE-MAYOR"):
            curr_pos = "VICE-MAYOR"
            master_dict[curr_pos] = []
        elif row[0].startswith("MEMBER, SANGGUNIANG BAYAN") or row[0].startswith("MEMBER, SANGGUNIANG PANLUNGSOD"):
            curr_pos = "LGU_COUNCIL"
            # get max number of councilors to vote for
            strNum = row[0].split("\n")[0].split(" ")[-1]
            try:
                max_councilor_board_slots = int(strNum)
            except:
                return None
            
            master_dict[curr_pos] = []
            
        # add support for BANGSAMORO
        else:
            # skip positions set to skip
            if include_senators == False and curr_pos == "SENATOR":
                continue
            if include_provincial == False and curr_pos in PROVINCIAL_POSITIONS:
                continue
            if include_local == False and curr_pos in LOCAL_POSITIONS:
                continue
            
            for candidate in row:
                if candidate == None:
                    continue
                splitted_candidate = candidate.split(" ")
                ballot_number = splitted_candidate.pop(0).removesuffix(".")  # pop the ballot number, leaving only the ballot number
                ballot_name = " ".join(splitted_candidate)
                
                # master_dict[curr_pos].append((ballot_number, ballot_name.replace("\n", " "), curr_pos))
                candidates.append((ballot_number, ballot_name.replace("\n", " "), curr_pos))
    
    # treat second page (temp_partylists)
    partylists = []

    if include_partylists == True:
        for i in range(5):
            for j in range(1,39):   # ignore the first row
                try:
                    entry:str = temp_partylists[j][i]

                    splitted_entry = entry.split(" ")
                    ballot_number = splitted_entry.pop(0)   # pop the ballot number, leaving only the name
                    ballot_name = " ".join(splitted_entry)

                    # partylists.append((ballot_number, ballot_name.replace("\n", " ", "PARTYLIST")))
                    candidates.append((ballot_number, ballot_name.replace("\n", " "), "PARTYLIST"))
                except:
                    continue
        master_dict["PARTYLIST"] = partylists

    # short-circuit when not a bangsamoro province
    if len(temp_bangsamoro) == 0:
        return {
            "max_provincial_board_slots": max_provincial_board_slots,
            "max_councilor_board_slots": max_councilor_board_slots,
            "candidates": list(filter(lambda candidate: candidate[0] != "", candidates))
        }

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
                
                # master_dict[curr_pos].append((ballot_number, ballot_name.replace("\n", " "),curr_pos))
                candidates.append((ballot_number, ballot_name.replace("\n", " "), curr_pos))

    return {
        "max_provincial_board_slots": max_provincial_board_slots,
        "max_councilor_board_slots": max_councilor_board_slots,
        "candidates": list(filter(lambda candidate: candidate[0] != "", candidates))
    }

def extract_from_region(region:str, link:str):
    driver.get(link)
    db = pg.connect(db_key, cursor_factory=pg.ClientCursor)
    
    root = driver.find_element(by=By.ID, value="accordionFlushExample")
    province_divs = root.find_elements(by=By.CLASS_NAME, value="accordion-item")
    
    i = 0
    for province in province_divs:
        lgus_wrapper_xpath = f"/html/body/div[3]/div[2]/div/div[2]/div/div[1]/div/div/div/div[{i+1}]/div/div/ul"
        province_name_wrapper = f"/html/body/div[3]/div[2]/div/div[2]/div/div[1]/div/div/div/div[{i+1}]/h2/button"

        # get links of lgus
        lgus = driver.find_element(by=By.XPATH, value=lgus_wrapper_xpath).find_elements(by=By.TAG_NAME, value="li")
        province_name = driver.find_element(by=By.XPATH, value=f"{province_name_wrapper}/span").get_attribute("innerHTML")

        # open accordion
        accordion_header = driver.find_element(by=By.XPATH, value=province_name_wrapper)
        driver.execute_script("arguments[0].click()", accordion_header)
        
        # create province
        province = None
        max_provincial_board = 0
        province_id = None
        governors = []
        vice_governors = []
    
        # iterate through LGUs
        j = 0
        for lgu in lgus:
            lgu_link = lgu.find_element(by=By.TAG_NAME, value="a")
            lgu_name = lgu_link.find_element(by=By.TAG_NAME, value="span").get_attribute("innerHTML")
            
            print(f"EXTRACTED: {lgu_name}")
            
            filename = f"{province_name}-{lgu_name}.pdf"
            
            try: 
                driver.execute_script(f"arguments[0].setAttribute('download', '{filename}');", lgu_link)
            except:
                print(f"arguments[0].setAttribute('download', '{filename}');")
                return
            
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((lgu_link)))
            # lgu_link.click()
            driver.execute_script("arguments[0].click()", lgu_link)
            
            # MAIN LOGIC
            # actually perform extraaction here
            time.sleep(2)

            res = None
            
            # check if governors and vice-governors are given
            if province == None:
                # first instance of province
                res = extract_candidates_from_file(f"temp/{filename}", include_senators=False, include_partylists=False)
                
                max_provincial_board = res["max_provincial_board_slots"]
                max_lgu_council = res["max_councilor_board_slots"]
                
                # set province
                province = province_name
                
                print(f"EXTRACTED: {province} (province)")
                
                # set governors
                governors = list(filter(lambda candidate: candidate[2] == "PROVINCIAL GOVERNOR", res["candidates"]))
                # set vice governors
                vice_governors = list(filter(lambda candidate: candidate[2] == "PROVINCIAL VICE-GOVERNOR", res["candidates"]))
                
                # save governors and vice governors under province
                combined_provincials = governors + vice_governors
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO province (name, region)
                    VALUES (%s, %s)
                    RETURNING province_id;
                    """, (province, region))
                province_id = cursor.fetchone()[0]
                db.commit()
                
                # for candidate in combined_provincials:
                with cursor.copy("COPY candidate (province_id, lgu_id, ballot_number, ballot_name, position) FROM STDIN") as copy:
                    for candidate in combined_provincials:
                        copy.write_row((province_id, None, int(candidate[0]), candidate[1], candidate[2]))
                db.commit()
                
                candidates = list(filter(lambda cand: cand[2] != "PROVINCIAL GOVERNOR" and cand[2] != "PROVINCIAL VICE-GOVERNOR", res["candidates"]))
                
                cursor.execute("""
                    INSERT INTO lgu (lgu, province_name, region, province_id, max_provincial_board, max_lgu_council)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING lgu_id;
                    """, (lgu_name, province_name, region, province_id, max_provincial_board, max_lgu_council))
                lgu_id = cursor.fetchone()[0]
                db.commit()
                
                # for candidate in combined_provincials:
                with cursor.copy("COPY candidate (lgu_id, province_id, ballot_number, ballot_name, position) FROM STDIN") as copy:
                    for candidate in candidates:
                        copy.write_row((lgu_id, province_id, int(candidate[0]), candidate[1], candidate[2]))
                db.commit()
            else:
                # don't include governors and vice governors
                res = extract_candidates_from_file(f"temp/{filename}", include_senators=False, include_provincial=False, include_partylists=False)
                
                max_lgu_council = res["max_councilor_board_slots"]

                candidates = list(filter(lambda cand: cand[2] != "PROVINCIAL GOVERNOR" and cand[2] != "PROVINCIAL VICE-GOVERNOR", res["candidates"]))
                
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO lgu (lgu, province_name, region, province_id, max_provincial_board, max_lgu_council)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING lgu_id;
                    """, (lgu_name, province_name, region, province_id, max_provincial_board, max_lgu_council))
                lgu_id = cursor.fetchone()[0]
                db.commit()
                
                # for candidate in combined_provincials:
                with cursor.copy("COPY candidate (lgu_id, province_id, ballot_number, ballot_name, position) FROM STDIN") as copy:
                    for candidate in candidates:
                        print(candidate)
                        copy.write_row((lgu_id, province_id, int(candidate[0]), candidate[1], candidate[2]))
                db.commit()
            
            os.remove(f"temp/{filename}")
            
        time.sleep(2)
        i = i + 1
    return

def extract_from_ncr(link:str):
    driver.get(link)
    db = pg.connect(db_key, cursor_factory=pg.ClientCursor)
    
    cities = driver.find_elements(by=By.CLASS_NAME, value="list-view")
    links = cities[0].find_elements(By.TAG_NAME, "li") + cities[1].find_elements(By.TAG_NAME, "li")
    
    i=0
    for link in links:
        lgu_link = link.find_element(by=By.TAG_NAME, value="a")
        lgu_name = lgu_link.get_attribute("innerHTML")
        
        print(f"EXTRACTED: {lgu_name}")
            
        filename = f"NCR-{lgu_name}.pdf"
            
        try: 
            driver.execute_script(f"arguments[0].setAttribute('download', '{filename}');", lgu_link)
        except:
            print(f"arguments[0].setAttribute('download', '{filename}');")
            return
            
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((lgu_link)))
        
        driver.execute_script("arguments[0].click()", lgu_link)
            
        # MAIN LOGIC
        # actually perform extraaction here
        time.sleep(2)
        
        # extract
        res = extract_candidates_from_file(f"temp/{filename}", include_senators=False, include_partylists=False, include_barmm_partylists=False, include_provincial=False)
        
        candidates = res["candidates"]
        max_lgu_council = res["max_councilor_board_slots"]
        
        # for candidate in candidates:
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO lgu (lgu, province_name, region, province_id, max_provincial_board, max_lgu_council)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING lgu_id;
            """, (lgu_name, None, "NCR", None, 0, max_lgu_council))
        lgu_id = cursor.fetchone()[0]
        db.commit()
    
        # for candidate in combined_provincials:
        with cursor.copy("COPY candidate (lgu_id, province_id, ballot_number, ballot_name, position) FROM STDIN") as copy:
            for candidate in candidates:
                copy.write_row((lgu_id, None, int(candidate[0]), candidate[1], candidate[2]))
        db.commit()
        
        os.remove(f"temp/{filename}")
    
    return

# sample_typical = "BADOC.pdf"0
# sample_barmm = "HADJI_MOHAMMAD_AJUL.pdf"
# sample_no_board="PANGASINAN-CITY OF DAGUPAN.pdf"

# traverse through COMELEC Site
regions = (
    ("NCR", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_NCR"),
    ("CAR", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_CAR"),
    ("NIR", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_NIR"),
    ("I", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R1"),
    ("II", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R2"),
    ("III", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R3"),
    ("IV-A", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R4A"),
    ("IV-B", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R4B"),
    ("V", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R5"),
    ("VI", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R6"),
    ("VII", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R7"),
    ("VIII", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R8"),
    ("IX", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R9"),
    ("X", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R10"),
    ("XI", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R11"),
    ("XII", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R12"),
    ("CARAGA", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_R13"),
    ("BARMM", "https://comelec.gov.ph/?r=2025NLE/2025BallotFace/BFT_BARMM")
)

def extract_all():
    # extract senators and partylists first
    national_positions = extract_candidates_from_file("temp/OV.pdf", include_local=False, include_provincial=False)
    senators = pd.DataFrame(list(filter(lambda cand: cand[2] == "SENATOR",national_positions["candidates"])), columns=["ballot_number", "ballot_name", "position"])
    partylists = pd.DataFrame(list(filter(lambda cand: cand[2] == "PARTYLIST",national_positions["candidates"])), columns=["ballot_number", "ballot_name", "position"])
    
    # save national positions
    senators.to_csv("data/senators.csv", index=False, header=False)
    partylists.to_csv("data/partylists.csv", index=False, header=False)
    
    for region in regions:
        if region[0] == "NCR":
            # special handler
            extract_from_ncr(region[1])
            continue
        extract_from_region(region[0], region[1])
    
    return

extract_all()