"""Point d'entrée de BiblioIIT : assemble Modèle, Contrôleur et Vue puis lance l'application."""
import argparse

from app.controllers.service import BiblioService
from app.models import donnees_demo
from app.models.depot_sqlite import DepotSQLite
from app.views.console import VueConsole


def main():
    parser = argparse.ArgumentParser(description="BiblioIIT - gestion de bibliothèque (console)")
    parser.add_argument("--db", default="biblioiit.db", help="fichier SQLite (défaut : biblioiit.db)")
    args = parser.parse_args()

    depot = DepotSQLite(args.db)
    if depot.nb_livres() == 0:
        donnees_demo.charger(depot)  # premier lancement : données de démonstration
    VueConsole(BiblioService(depot)).lancer()
    depot.fermer()


if __name__ == "__main__":
    main()
