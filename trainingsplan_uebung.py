
trainingsplan = {
    "name": "Oberkörper",
    "uebungen":  [
        "Bankdrücken",
        "Schrägbankdrücken",
        "Kabelzug Rudern",
        "Latzug",
        "Schulterdrücken",
        "Seitheben",
        "Bizepscurls"
    ]
}




def zeige_trainingsplan(plan):
    if type(plan) == str and plan is not NotImplemented :
        print("Trainingsplan:", plan["name"])
        for uebung in plan["uebungen"]:
            print("  -", uebung)


def add_uebung(plan,uebung):
    plan["uebungen"].append(uebung)

def del_uebung(plan,uebung):
    plan["uebungen"].remove(uebung)

def new_trainingsplan():
    return {
        "name": input("Name:"),
        "uebungen": []
    }

def del_trainingsplan(plan):
    del trainingsplan

zeige_trainingsplan(trainingsplan)

add_uebung(trainingsplan,"Trizepsdrücken")
del_uebung(trainingsplan,"Kabelzug Rudern")

zeige_trainingsplan(trainingsplan)


def start_menue() -> None:
    while True:
        print("\n1 = Neuer Plan, 2 = Anzeigen, 3 = Hinzufügen Übung, 4 = Entfernen Übung, 5 = Entfernen Trainingsplan, 0 = Beenden")
        inp = input("Bitte Eingabe:")

        if inp == "1":
            trainingsplan = new_trainingsplan()
        elif inp == "2":
            plan = input("Trainingsplan:")
            zeige_trainingsplan(plan)
        elif inp == "3":
            uebung = input("Neue Uebung:")
            add_uebung(trainingsplan,uebung)
        elif inp == "4":
            uebung = input("Uebung zu entfernen:")
            del_uebung(trainingsplan,uebung)
        elif inp == "5":
            del_trainingsplan(trainingsplan)
        elif inp == "0":
            break

start_menue()