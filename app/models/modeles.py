
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Livre:
    code: str
    titre: str
    auteur: str
    annee: int
    categorie: str = "Général"
    exemplaires: int = 1  # nombre de copies physiques


@dataclass
class Adherent:
    matricule: str
    nom: str
    prenom: str
    date_inscription: date


@dataclass
class Emprunt:
    id: int
    code_livre: str
    matricule: str
    date_emprunt: date
    retour_prevu: date
    retour_reel: Optional[date] = None
    prolongations: int = 0

    @property
    def en_cours(self) -> bool:
        return self.retour_reel is None


@dataclass
class Reservation:
    id: int
    code_livre: str
    matricule: str
    date_reservation: date
    active: bool = True
