def get_bank(BankList: list, BankName: str):
    exact_match = [b for b in BankList if BankName.lower() == b["name"].lower()]
    if len(exact_match) == 1:
        return exact_match[0]
    
    elif len(exact_match) == 0:
        tentative_match = [b for b in BankList if BankName in b["name"]]
        if len(tentative_match) == 0:
            tentative_match = [b for b in BankList if BankName.lower() in b["name"].lower()]

        if len(tentative_match) == 1:
            return tentative_match[0]
        elif len(tentative_match) == 0:
            print(f"No valid candidates found for Bank Name: <{BankName}>")
        else:
            print(f"Multiple banks found with name compatible with {BankName}:")
            for b in tentative_match:
                print(f"- {b['name']} ({b['country']})")
            return tentative_match

    else:
        print(f"Multiple banks found with name {BankName}:")
        for b in exact_match:
            print(f"- {b['name']} ({b['country']})")
            return exact_match
        
    return None


def get_bank_key(bank):
    bank_key = f"{bank['name']}_{bank['country']}"
    #print(f"Let's load bank session for {bank["name"]} (bank_key={bank_key})...")
    return bank_key
