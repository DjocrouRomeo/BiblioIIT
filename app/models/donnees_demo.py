
from datetime import date

from .modeles import Adherent, Livre

LIVRES = [
    Livre("L001", "Le Vieux Nègre et la médaille", "Ferdinand Oyono", 1956, "Littérature africaine", 2),
    Livre("L002", "Les Soleils des indépendances", "Ahmadou Kourouma", 1968, "Littérature africaine", 1),
    Livre("L003", "Germinal", "Émile Zola", 1885, "Roman", 2),
    Livre("L004", "Allah n'est pas obligé", "Ahmadou Kourouma", 2000, "Littérature africaine", 2),
    Livre("L005", "Une si longue lettre", "Mariama Bâ", 1979, "Littérature africaine", 1),
    Livre("L006", "Les Misérables", "Victor Hugo", 1862, "Roman", 1),
    Livre("L007", "Le Petit Prince", "Antoine de Saint-Exupéry", 1943, "Conte", 3),
]

ADHERENTS = [
    Adherent("E2026-001", "Djocrou", "Romeo", date(2026, 9, 15)),
    Adherent("E2026-002", "Blé", "Goudé", date(2026, 9, 15)),
    Adherent("E2026-003", "Diabagaté", "Hassane", date(2026, 9, 20)),
]


def charger(depot):
    for l in LIVRES:
        depot.ajouter_livre(l)
    for a in ADHERENTS:
        depot.ajouter_adherent(a)
