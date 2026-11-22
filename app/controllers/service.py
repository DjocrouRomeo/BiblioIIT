
from dataclasses import dataclass
from datetime import date
from typing import Callable, List, Optional, Tuple

from app.models import regles
from app.models.depot_sqlite import DepotSQLite
from app.models.modeles import Adherent, Emprunt, Livre


class BiblioError(Exception):
    """Erreur métier affichable telle quelle à l'utilisateur."""


@dataclass
class ResultatRetour:
    emprunt: Emprunt
    livre: Livre
    jours_retard: int
    amende: int
    reservataire: Optional[Adherent]  # à prévenir si le livre était réservé


@dataclass
class LigneRetard:
    emprunt: Emprunt
    livre: Livre
    adherent: Adherent
    jours_retard: int
    amende: int


class BiblioService:
    def __init__(self, depot: DepotSQLite, aujourdhui: Callable[[], date] = date.today):
        self.depot = depot
        self._aujourdhui = aujourdhui

    # ---------- utilitaires ----------
    def _livre(self, code: str) -> Livre:
        livre = self.depot.get_livre(code.strip().upper())
        if not livre:
            raise BiblioError(f"Aucun livre avec le code « {code} ».")
        return livre

    def _adherent(self, matricule: str) -> Adherent:
        a = self.depot.get_adherent(matricule.strip().upper())
        if not a:
            raise BiblioError(f"Aucun adhérent avec le matricule « {matricule} ».")
        return a

    def disponibles(self, livre: Livre) -> int:
        return livre.exemplaires - self.depot.emprunts_en_cours_livre(livre.code)

    # ---------- catalogue ----------
    def rechercher(self, mot: str) -> List[Tuple[Livre, int]]:
        return [(l, self.disponibles(l)) for l in self.depot.rechercher_livres(mot.strip())]

    def fiche_livre(self, code: str) -> Tuple[Livre, int, int]:
        livre = self._livre(code)
        return livre, self.disponibles(livre), len(self.depot.reservations_actives(livre.code))

    # ---------- emprunts ----------
    def emprunter(self, code: str, matricule: str) -> Emprunt:
        livre, adherent = self._livre(code), self._adherent(matricule)
        today = self._aujourdhui()
        if self.depot.emprunt_ouvert(livre.code, adherent.matricule):
            raise BiblioError(f"Vous avez déjà emprunté « {livre.titre} ».")
        ok, motif = regles.peut_emprunter(
            adherent.date_inscription,
            len(self.depot.emprunts_en_cours(adherent.matricule)),
            any(e.matricule == adherent.matricule for e in self.depot.emprunts_en_retard(today)),
            self.depot.amendes_impayees(adherent.matricule),
            today)
        if not ok:
            raise BiblioError(f"Emprunt refusé : {motif}.")
        if self.disponibles(livre) <= 0:
            raise BiblioError(f"Le livre « {livre.titre} » est déjà emprunté "
                              f"(vous pouvez le réserver).")
        resas = self.depot.reservations_actives(livre.code)
        if resas and resas[0].matricule != adherent.matricule:
            raise BiblioError(f"Le livre « {livre.titre} » est réservé par un autre adhérent.")
        if resas and resas[0].matricule == adherent.matricule:
            self.depot.desactiver_reservation(resas[0].id)
        retour = regles.date_retour_prevue(today)
        eid = self.depot.creer_emprunt(livre.code, adherent.matricule, today, retour)
        return Emprunt(eid, livre.code, adherent.matricule, today, retour)

    def rendre(self, code: str, matricule: str) -> ResultatRetour:
        livre, adherent = self._livre(code), self._adherent(matricule)
        emprunt = self.depot.emprunt_ouvert(livre.code, adherent.matricule)
        if not emprunt:
            raise BiblioError(f"{adherent.prenom} {adherent.nom} n'a pas emprunté « {livre.titre} ».")
        today = self._aujourdhui()
        self.depot.cloturer_emprunt(emprunt.id, today)
        retard = regles.jours_de_retard(emprunt.retour_prevu, today)
        amende = regles.calcul_amende(retard)
        if amende > 0:
            self.depot.creer_amende(adherent.matricule, emprunt.id, amende)
        resas = self.depot.reservations_actives(livre.code)
        suivant = self.depot.get_adherent(resas[0].matricule) if resas else None
        emprunt.retour_reel = today
        return ResultatRetour(emprunt, livre, retard, amende, suivant)

    def prolonger(self, code: str, matricule: str) -> Emprunt:
        livre, adherent = self._livre(code), self._adherent(matricule)
        emprunt = self.depot.emprunt_ouvert(livre.code, adherent.matricule)
        if not emprunt:
            raise BiblioError(f"{adherent.prenom} {adherent.nom} n'a pas emprunté « {livre.titre} ».")
        resas = self.depot.reservations_actives(livre.code)
        autre = any(r.matricule != adherent.matricule for r in resas)
        ok, motif = regles.peut_prolonger(emprunt.retour_prevu, emprunt.prolongations,
                                          autre, self._aujourdhui())
        if not ok:
            raise BiblioError(f"Prolongation impossible : {motif}.")
        emprunt.retour_prevu = regles.nouvelle_date_retour(emprunt.retour_prevu)
        self.depot.prolonger_emprunt(emprunt.id, emprunt.retour_prevu)
        emprunt.prolongations += 1
        return emprunt

    def reserver(self, code: str, matricule: str) -> int:
        """Retourne la position dans la file d'attente."""
        livre, adherent = self._livre(code), self._adherent(matricule)
        if self.disponibles(livre) > 0:
            raise BiblioError(f"« {livre.titre} » est disponible : empruntez-le directement.")
        if self.depot.emprunt_ouvert(livre.code, adherent.matricule):
            raise BiblioError("Vous avez déjà ce livre en votre possession.")
        resas = self.depot.reservations_actives(livre.code)
        if any(r.matricule == adherent.matricule for r in resas):
            raise BiblioError("Vous avez déjà réservé ce livre.")
        self.depot.creer_reservation(livre.code, adherent.matricule, self._aujourdhui())
        return len(resas) + 1

    # ---------- adhérents ----------
    def inscrire(self, nom: str, prenom: str) -> Adherent:
        nom, prenom = nom.strip(), prenom.strip()
        if not nom or not prenom:
            raise BiblioError("Le nom et le prénom sont obligatoires.")
        today = self._aujourdhui()
        a = Adherent(self.depot.prochain_matricule(today.year), nom, prenom, today)
        self.depot.ajouter_adherent(a)
        return a

    def consulter_adherent(self, matricule: str):
        a = self._adherent(matricule)
        en_cours = self.depot.emprunts_en_cours(a.matricule)
        historique = self.depot.historique(a.matricule)
        return (a, [(e, self._livre(e.code_livre)) for e in en_cours],
                [(e, self._livre(e.code_livre)) for e in historique],
                self.depot.amendes_impayees(a.matricule))

    def payer_amendes(self, matricule: str) -> int:
        a = self._adherent(matricule)
        du = self.depot.amendes_impayees(a.matricule)
        if du == 0:
            raise BiblioError("Aucune amende à payer.")
        self.depot.payer_amendes(a.matricule)
        return du

    # ---------- suivi ----------
    def retards(self) -> List[LigneRetard]:
        today, lignes = self._aujourdhui(), []
        for e in self.depot.emprunts_en_retard(today):
            j = regles.jours_de_retard(e.retour_prevu, today)
            lignes.append(LigneRetard(e, self._livre(e.code_livre), self._adherent(e.matricule),
                                      j, regles.calcul_amende(j)))
        return lignes

    def statistiques(self):
        today = self._aujourdhui()
        emprunts = self.depot.tous_les_emprunts()
        en_retard = sum(1 for e in emprunts
                        if regles.jours_de_retard(e.retour_prevu, today, e.retour_reel) > 0)
        taux = (100.0 * en_retard / len(emprunts)) if emprunts else 0.0
        return self.depot.plus_empruntes(5), len(emprunts), taux

    # ---------- administration ----------
    def ajouter_livre(self, code, titre, auteur, annee, categorie, exemplaires) -> Livre:
        code = code.strip().upper()
        if not code or not titre.strip() or not auteur.strip():
            raise BiblioError("Code, titre et auteur sont obligatoires.")
        if self.depot.get_livre(code):
            raise BiblioError(f"Le code « {code} » existe déjà.")
        if exemplaires < 1:
            raise BiblioError("Il faut au moins 1 exemplaire.")
        livre = Livre(code, titre.strip(), auteur.strip(), annee, categorie.strip() or "Général", exemplaires)
        self.depot.ajouter_livre(livre)
        return livre

    def modifier_livre(self, code, titre, auteur, annee, categorie, exemplaires) -> Livre:
        ancien = self._livre(code)
        if exemplaires < self.depot.emprunts_en_cours_livre(ancien.code):
            raise BiblioError("Moins d'exemplaires que d'emprunts en cours : impossible.")
        livre = Livre(ancien.code, titre.strip() or ancien.titre, auteur.strip() or ancien.auteur,
                      annee, categorie.strip() or ancien.categorie, exemplaires)
        self.depot.modifier_livre(livre)
        return livre

    def retirer_livre(self, code: str) -> Livre:
        livre = self._livre(code)
        if self.depot.emprunts_en_cours_livre(livre.code) > 0:
            raise BiblioError("Impossible de retirer un livre actuellement emprunté.")
        self.depot.supprimer_livre(livre.code)
        return livre
