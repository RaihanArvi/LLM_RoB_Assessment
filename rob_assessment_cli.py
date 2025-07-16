import rob_assessment

def main_menu():
    while True:
        splash_screen()
        print("Main Menu:")
        print("[1] PDF Input")
        print("[2] Plain Text Input")
        print("[q] Quit")
        choice = input("Select an option: ").strip()

        if choice == "1":
            pdf_input_menu()
        elif choice == "2":
            plain_text_menu()
        elif choice.lower() == "q":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Try again.")

def pdf_input_menu():
    while True:
        print("\nPDF Input Menu:")
        print("[1] Upload File")
        print("[2] Start assessment using Stored Files")
        print("[3] Get Number of All Stored Files")
        print("[4] Delete All Stored Files")
        print("[b] Back to Main Menu")
        choice = input("Select an option: ").strip()

        if choice == "1":
            files_dict = rob_assessment.upload_all_pdfs()
        elif choice == "2":
            print("Starting assessment from stored files...")
            dict = rob_assessment.get_file_name_id_dict()
            rob_assessment.process_pdf_stored_in_cloud(dict)

        elif choice == "3":
            count_stored_files = rob_assessment.get_number_of_stored_files()
            print(f"Stored files count: "+str(count_stored_files))
        elif choice == "4":
            count_stored_files = rob_assessment.get_number_of_stored_files()
            rob_assessment.delete_all_stored_files()
            print(str(count_stored_files)+" files have been deleted.")
            print("All stored files has been deleted.")
        elif choice.lower() == "b":
            break
        else:
            print("Invalid choice. Try again.")

def plain_text_menu():
    print("\nPlain Text Assessment:")
    text = input("Enter text to assess: ").strip()

def start_assessment(input_data):
    print(f"Starting assessment on: {input_data}")
    # Replace this with actual assessment logic

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