"""MODÈLE - règles métier pures (pas d'input(), pas de SQL) : faciles à tester."""
from datetime import date, timedelta
from typing import Optional, Tuple

DUREE_PRET = 14               # jours
DUREE_PROLONGATION = 14       # jours
MAX_PROLONGATIONS = 1
QUOTA_EMPRUNTS = 3            # livres simultanés par adhérent
AMENDE_PAR_JOUR = 100         # FCFA
AMENDE_PLAFOND = 5000         # FCFA
VALIDITE_INSCRIPTION = 365    # jours


def date_retour_prevue(date_emprunt: date) -> date:
    return date_emprunt + timedelta(days=DUREE_PRET)


def jours_de_retard(retour_prevu: date, aujourdhui: date,
                    retour_reel: Optional[date] = None) -> int:
    reference = retour_reel or aujourdhui
    return max(0, (reference - retour_prevu).days)


def calcul_amende(jours_retard: int) -> int:
    return min(jours_retard * AMENDE_PAR_JOUR, AMENDE_PLAFOND)


def inscription_valide(date_inscription: date, aujourdhui: date) -> bool:
    return (aujourdhui - date_inscription).days <= VALIDITE_INSCRIPTION


def peut_emprunter(date_inscription: date, nb_emprunts_en_cours: int,
                   a_un_retard: bool, amendes_impayees: int,
                   aujourdhui: date) -> Tuple[bool, str]:
    if not inscription_valide(date_inscription, aujourdhui):
        return False, "inscription expirée, veuillez la renouveler"
    if a_un_retard:
        return False, "l'adhérent a un livre en retard à rendre"
    if amendes_impayees > 0:
        return False, f"amende impayée de {amendes_impayees} FCFA"
    if nb_emprunts_en_cours >= QUOTA_EMPRUNTS:
        return False, f"quota atteint ({QUOTA_EMPRUNTS} livres maximum)"
    return True, ""


def peut_prolonger(retour_prevu: date, prolongations: int,
                   reserve_par_un_autre: bool, aujourdhui: date) -> Tuple[bool, str]:
    if prolongations >= MAX_PROLONGATIONS:
        return False, "prolongation déjà utilisée"
    if aujourdhui > retour_prevu:
        return False, "emprunt en retard, rendez le livre"
    if reserve_par_un_autre:
        return False, "le livre est réservé par un autre adhérent"
    return True, ""


def nouvelle_date_retour(retour_prevu: date) -> date:
    return retour_prevu + timedelta(days=DUREE_PROLONGATION)
