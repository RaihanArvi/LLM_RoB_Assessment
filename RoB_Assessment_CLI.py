from RoBAssessment import Assessment as assess
from RoBAssessment import AllCriteria
from RoBAssessment import PerCriteria

def main_menu():
    while True:
        splash_screen()
        print("Main Menu")
        print("Choose Assessment Mode:")
        print("[1] Assess Criteria one-by-one per Paper")
        print("[2] Assess All Criteria per Paper")
        print("[q] Quit")
        choice = input("Select an option: ").strip()

        if choice == "1":
            per_criteria_mode()
        elif choice == "2":
            all_criteria_mode()
        elif choice.lower() == "q":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Try again.")
def all_criteria_mode():
    while True:
        print("All Criteria Mode")
        print("Choose Input Option:")
        print("[1] PDF Input")
        print("[2] Plain Text Input")
        print("[b] Previous Menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            all_criteria_pdf_input_menu()
        elif choice == "2":
            all_criteria_plain_text_menu()
        elif choice.lower() == "b":
            break
        else:
            print("Invalid choice. Try again.")

def per_criteria_mode():
    while True:
        print("Per Criteria Mode")
        print("Choose Input Option:")
        print("[1] PDF Input")
        print("[2] Plain Text Input")
        print("[b] Previous Menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            per_criteria_pdf_input_menu()
        elif choice == "2":
            per_criteria_plain_text_menu()
        elif choice.lower() == "b":
            break
        else:
            print("Invalid choice. Try again.")

### All Criteria ###
def all_criteria_pdf_input_menu():
    while True:
        print("\nPDF Input Menu:")
        print("[1] Upload File")
        print("[2] Start assessment using Stored Files")
        print("[3] Get Number of All Stored Files")
        print("[4] Delete All Stored Files")
        print("[b] Previous Menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            assess.upload_all_pdfs()
        elif choice == "2":
            print("Starting assessment from stored files...")
            dict = assess.get_file_name_id_dict()
            AllCriteria.process_pdf_stored_in_cloud(dict)

        elif choice == "3":
            count_stored_files = assess.get_number_of_stored_files()
            print(f"Stored files count: "+str(count_stored_files))
        elif choice == "4":
            count_stored_files = assess.get_number_of_stored_files()
            assess.delete_all_stored_files()
            print(str(count_stored_files)+" files have been deleted.")
            print("All stored files has been deleted.")
        elif choice.lower() == "b":
            break
        else:
            print("Invalid choice. Try again.")

def all_criteria_plain_text_menu():
    while True:
        print("\nStart plain text assessment?")
        print("[1] Start")
        print("[b] Previous Menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            print("\nStarting risk-of-bias assessment...")
            AllCriteria.process_plain_text()
        elif choice.lower() == "b":
            break
        else:
            print("Invalid choice. Try again.")


### Per Criteria ###
def per_criteria_pdf_input_menu():
    while True:
        print("\nPDF Input Menu:")
        print("[1] Upload File")
        print("[2] Start assessment using Stored Files")
        print("[3] Get Number of All Stored Files")
        print("[4] Delete All Stored Files")
        print("[b] Previous Menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            assess.upload_all_pdfs()
        elif choice == "2":
            print("Starting assessment from stored files...")
            dict = assess.get_file_name_id_dict()
            PerCriteria.process_pdf_stored_in_cloud(dict)

        elif choice == "3":
            count_stored_files = assess.get_number_of_stored_files()
            print(f"Stored files count: "+str(count_stored_files))
        elif choice == "4":
            count_stored_files = assess.get_number_of_stored_files()
            assess.delete_all_stored_files()
            print(str(count_stored_files)+" files have been deleted.")
            print("All stored files has been deleted.")
        elif choice.lower() == "b":
            break
        else:
            print("Invalid choice. Try again.")

def per_criteria_plain_text_menu():
    while True:
        print("\nStart plain text assessment?")
        print("[1] Start")
        print("[b] Previous Menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            print("\nStarting risk-of-bias assessment...")
            PerCriteria.process_plain_text()
        elif choice.lower() == "b":
            break
        else:
            print("Invalid choice. Try again.")

def splash_screen():
    print(r"""
           _____ _____   _____   _____  _____   ____       _ ______ _____ _______ 
     /\   |_   _|  __ \ / ____| |  __ \|  __ \ / __ \     | |  ____/ ____|__   __|
    /  \    | | | |__) | (___   | |__) | |__) | |  | |    | | |__ | |       | |   
   / /\ \   | | |  _  / \___ \  |  ___/|  _  /| |  | |_   | |  __|| |       | |   
  / ____ \ _| |_| | \ \ ____) | | |    | | \ \| |__| | |__| | |___| |____   | |   
 /_/    \_\_____|_|  \_\_____/  |_|    |_|  \_\\____/ \____/|______\_____|  |_|   
                                                                                  
      LLM-Based Risk-of-Bias Assessment Tool
    """)

if __name__ == "__main__":
    main_menu()