"""VUE - interface console : affichage et saisies uniquement.

La vue ne contient AUCUNE règle métier : elle délègue au contrôleur (BiblioService)
et affiche les résultats ou les messages d'erreur (BiblioError).
"""
from datetime import date
from typing import Callable

from app.controllers.service import BiblioError, BiblioService

MENU = """
=== BiblioIIT ===
-- Catalogue --
1. Rechercher un livre (titre, auteur, mot-clé, catégorie)
2. Consulter la fiche d'un livre
-- Emprunts --
3. Emprunter
4. Rendre
5. Prolonger un emprunt
6. Réserver un livre déjà emprunté
-- Adhérents --
7. Inscrire un adhérent
8. Consulter un adhérent (emprunts, historique, amendes)
-- Suivi --
9. Retards et amendes
10. Statistiques
-- Administration --
11. Ajouter / modifier / retirer un livre
12. Encaisser les amendes d'un adhérent
0. Quitter"""


def fmt(d: date) -> str:
    return d.strftime("%d/%m/%Y")


class VueConsole:
    def __init__(self, service: BiblioService,
                 entree: Callable[[str], str] = input,
                 sortie: Callable[..., None] = print):
        self.s = service
        self._in = entree
        self._out = sortie
        self.actions = {
            "1": self.rechercher, "2": self.fiche, "3": self.emprunter, "4": self.rendre,
            "5": self.prolonger, "6": self.reserver, "7": self.inscrire,
            "8": self.consulter_adherent, "9": self.retards, "10": self.statistiques,
            "11": self.admin_livre, "12": self.payer,
        }

    # ---------- boucle principale ----------
    def lancer(self):
        while True:
            self._out(MENU)
            choix = self._in("Votre choix : ").strip()
            if choix == "0":
                self._out("Au revoir !")
                return
            action = self.actions.get(choix)
            if not action:
                self._out("Choix invalide, tapez un numéro du menu.")
                continue
            try:
                action()
            except BiblioError as e:
                self._out(f"Impossible : {e}")
            except ValueError:
                self._out("Impossible : saisie numérique invalide.")

    # ---------- helpers d'affichage ----------
    def _ligne_livre(self, livre, dispo):
        return (f"  {livre.code}  {livre.titre} — {livre.auteur} ({livre.annee}) "
                f"[{dispo}/{livre.exemplaires} dispo]")

    # ---------- actions ----------
    def rechercher(self):
        mot = self._in("Mot-clé : ")
        resultats = self.s.rechercher(mot)
        if not resultats:
            self._out("Aucun livre trouvé.")
        for livre, dispo in resultats:
            self._out(self._ligne_livre(livre, dispo))

    def fiche(self):
        livre, dispo, nb_resa = self.s.fiche_livre(self._in("Code du livre : "))
        self._out(f"  {livre.code} — {livre.titre}\n  Auteur : {livre.auteur} ({livre.annee})\n"
                  f"  Catégorie : {livre.categorie}\n  Exemplaires : {dispo} disponible(s) sur "
                  f"{livre.exemplaires}\n  Réservations en attente : {nb_resa}")

    def emprunter(self):
        code, mat = self._in("Code du livre : "), self._in("Matricule : ")
        e = self.s.emprunter(code, mat)
        self._out(f"Emprunt enregistré. Retour prévu le {fmt(e.retour_prevu)}.")

    def rendre(self):
        code, mat = self._in("Code du livre : "), self._in("Matricule : ")
        r = self.s.rendre(code, mat)
        self._out(f"Retour enregistré : « {r.livre.titre} ».")
        if r.amende:
            self._out(f"Retard de {r.jours_retard} jour(s) : amende de {r.amende} FCFA.")
        if r.reservataire:
            self._out(f"Livre réservé : prévenir {r.reservataire.prenom} {r.reservataire.nom} "
                      f"({r.reservataire.matricule}).")

    def prolonger(self):
        code, mat = self._in("Code du livre : "), self._in("Matricule : ")
        e = self.s.prolonger(code, mat)
        self._out(f"Emprunt prolongé. Nouveau retour prévu le {fmt(e.retour_prevu)}.")

    def reserver(self):
        code, mat = self._in("Code du livre : "), self._in("Matricule : ")
        pos = self.s.reserver(code, mat)
        self._out(f"Réservation enregistrée. Position dans la file : {pos}.")

    def inscrire(self):
        nom, prenom = self._in("Nom : "), self._in("Prénom : ")
        a = self.s.inscrire(nom, prenom)
        self._out(f"Adhérent inscrit. Matricule : {a.matricule} (valable 1 an).")

    def consulter_adherent(self):
        a, en_cours, historique, amendes = self.s.consulter_adherent(self._in("Matricule : "))
        self._out(f"  {a.prenom} {a.nom} ({a.matricule}) — inscrit le {fmt(a.date_inscription)}")
        self._out("  Emprunts en cours :" + ("" if en_cours else " aucun"))
        for e, l in en_cours:
            self._out(f"    {l.code} {l.titre} — retour prévu le {fmt(e.retour_prevu)}")
        self._out(f"  Historique : {len(historique)} emprunt(s)")
        for e, l in historique:
            rendu = fmt(e.retour_reel) if e.retour_reel else "en cours"
            self._out(f"    {l.code} {l.titre} — emprunté le {fmt(e.date_emprunt)}, rendu : {rendu}")
        self._out(f"  Amendes impayées : {amendes} FCFA")

    def retards(self):
        lignes = self.s.retards()
        if not lignes:
            self._out("Aucun retard.")
        for r in lignes:
            self._out(f"  {r.livre.code} {r.livre.titre} — {r.adherent.prenom} {r.adherent.nom} "
                      f"({r.adherent.matricule}) : {r.jours_retard} jour(s), amende {r.amende} FCFA")

    def statistiques(self):
        top, total, taux = self.s.statistiques()
        self._out(f"  Emprunts au total : {total} — taux de retard : {taux:.1f} %")
        self._out("  Livres les plus empruntés :" + ("" if top else " aucun"))
        for code, titre, n in top:
            self._out(f"    {code} {titre} : {n} emprunt(s)")

    def admin_livre(self):
        op = self._in("(a)jouter, (m)odifier ou (r)etirer ? ").strip().lower()
        if op == "r":
            l = self.s.retirer_livre(self._in("Code du livre : "))
            self._out(f"Livre retiré : {l.titre}.")
        elif op in ("a", "m"):
            code = self._in("Code : ")
            titre, auteur = self._in("Titre : "), self._in("Auteur : ")
            annee = int(self._in("Année : "))
            cat = self._in("Catégorie : ")
            ex = int(self._in("Nombre d'exemplaires : "))
            f = self.s.ajouter_livre if op == "a" else self.s.modifier_livre
            l = f(code, titre, auteur, annee, cat, ex)
            self._out(f"Livre {'ajouté' if op == 'a' else 'modifié'} : {l.code} {l.titre}.")
        else:
            self._out("Choix invalide.")

    def payer(self):
        montant = self.s.payer_amendes(self._in("Matricule : "))
        self._out(f"Paiement de {montant} FCFA enregistré.")
