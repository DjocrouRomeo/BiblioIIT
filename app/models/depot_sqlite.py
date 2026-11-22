"""MODÈLE - accès aux données SQLite (CRUD et requêtes, aucune règle métier)."""
import sqlite3
from datetime import date
from typing import List, Optional

from .modeles import Adherent, Emprunt, Livre, Reservation

SCHEMA = """
CREATE TABLE IF NOT EXISTS livres (
    code TEXT PRIMARY KEY, titre TEXT NOT NULL, auteur TEXT NOT NULL,
    annee INTEGER, categorie TEXT, exemplaires INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS adherents (
    matricule TEXT PRIMARY KEY, nom TEXT NOT NULL, prenom TEXT NOT NULL,
    date_inscription TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS emprunts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, code_livre TEXT NOT NULL,
    matricule TEXT NOT NULL, date_emprunt TEXT NOT NULL, retour_prevu TEXT NOT NULL,
    retour_reel TEXT, prolongations INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, code_livre TEXT NOT NULL,
    matricule TEXT NOT NULL, date_reservation TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS amendes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, matricule TEXT NOT NULL,
    emprunt_id INTEGER NOT NULL, montant INTEGER NOT NULL, payee INTEGER NOT NULL DEFAULT 0);
"""


def _d(texte: Optional[str]) -> Optional[date]:
    return date.fromisoformat(texte) if texte else None


class DepotSQLite:
    def __init__(self, chemin: str = ":memory:"):
        self.conn = sqlite3.connect(chemin)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def fermer(self):
        self.conn.close()

    # ---------- convertisseurs ----------
    @staticmethod
    def _livre(r) -> Livre:
        return Livre(r["code"], r["titre"], r["auteur"], r["annee"], r["categorie"], r["exemplaires"])

    @staticmethod
    def _emprunt(r) -> Emprunt:
        return Emprunt(r["id"], r["code_livre"], r["matricule"], _d(r["date_emprunt"]),
                       _d(r["retour_prevu"]), _d(r["retour_reel"]), r["prolongations"])

    @staticmethod
    def _resa(r) -> Reservation:
        return Reservation(r["id"], r["code_livre"], r["matricule"],
                           _d(r["date_reservation"]), bool(r["active"]))

    # ---------- livres ----------
    def ajouter_livre(self, l: Livre):
        self.conn.execute("INSERT INTO livres VALUES (?,?,?,?,?,?)",
                          (l.code, l.titre, l.auteur, l.annee, l.categorie, l.exemplaires))
        self.conn.commit()

    def modifier_livre(self, l: Livre):
        self.conn.execute("UPDATE livres SET titre=?, auteur=?, annee=?, categorie=?, exemplaires=? WHERE code=?",
                          (l.titre, l.auteur, l.annee, l.categorie, l.exemplaires, l.code))
        self.conn.commit()

    def supprimer_livre(self, code: str):
        self.conn.execute("DELETE FROM livres WHERE code=?", (code,))
        self.conn.commit()

    def get_livre(self, code: str) -> Optional[Livre]:
        r = self.conn.execute("SELECT * FROM livres WHERE code=?", (code,)).fetchone()
        return self._livre(r) if r else None

    def nb_livres(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM livres").fetchone()[0]

    def rechercher_livres(self, mot: str) -> List[Livre]:
        m = f"%{mot.lower()}%"
        rows = self.conn.execute(
            "SELECT * FROM livres WHERE lower(titre) LIKE ? OR lower(auteur) LIKE ? "
            "OR lower(categorie) LIKE ? OR lower(code) LIKE ? ORDER BY code", (m, m, m, m)).fetchall()
        return [self._livre(r) for r in rows]

    # ---------- adhérents ----------
    def ajouter_adherent(self, a: Adherent):
        self.conn.execute("INSERT INTO adherents VALUES (?,?,?,?)",
                          (a.matricule, a.nom, a.prenom, a.date_inscription.isoformat()))
        self.conn.commit()

    def get_adherent(self, matricule: str) -> Optional[Adherent]:
        r = self.conn.execute("SELECT * FROM adherents WHERE matricule=?", (matricule,)).fetchone()
        return Adherent(r["matricule"], r["nom"], r["prenom"], _d(r["date_inscription"])) if r else None

    def prochain_matricule(self, annee: int) -> str:
        n = self.conn.execute("SELECT COUNT(*) FROM adherents WHERE matricule LIKE ?",
                              (f"E{annee}-%",)).fetchone()[0]
        return f"E{annee}-{n + 1:03d}"

    # ---------- emprunts ----------
    def creer_emprunt(self, code: str, matricule: str, jour: date, retour_prevu: date) -> int:
        cur = self.conn.execute(
            "INSERT INTO emprunts (code_livre, matricule, date_emprunt, retour_prevu) VALUES (?,?,?,?)",
            (code, matricule, jour.isoformat(), retour_prevu.isoformat()))
        self.conn.commit()
        return cur.lastrowid

    def emprunts_en_cours_livre(self, code: str) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM emprunts WHERE code_livre=? AND retour_reel IS NULL",
                                 (code,)).fetchone()[0]

    def emprunts_en_cours(self, matricule: str) -> List[Emprunt]:
        rows = self.conn.execute("SELECT * FROM emprunts WHERE matricule=? AND retour_reel IS NULL "
                                 "ORDER BY id", (matricule,)).fetchall()
        return [self._emprunt(r) for r in rows]

    def emprunt_ouvert(self, code: str, matricule: str) -> Optional[Emprunt]:
        r = self.conn.execute("SELECT * FROM emprunts WHERE code_livre=? AND matricule=? "
                              "AND retour_reel IS NULL", (code, matricule)).fetchone()
        return self._emprunt(r) if r else None

    def cloturer_emprunt(self, emprunt_id: int, jour: date):
        self.conn.execute("UPDATE emprunts SET retour_reel=? WHERE id=?", (jour.isoformat(), emprunt_id))
        self.conn.commit()

    def prolonger_emprunt(self, emprunt_id: int, nouveau_retour: date):
        self.conn.execute("UPDATE emprunts SET retour_prevu=?, prolongations=prolongations+1 WHERE id=?",
                          (nouveau_retour.isoformat(), emprunt_id))
        self.conn.commit()

    def historique(self, matricule: str) -> List[Emprunt]:
        rows = self.conn.execute("SELECT * FROM emprunts WHERE matricule=? ORDER BY id", (matricule,)).fetchall()
        return [self._emprunt(r) for r in rows]

    def tous_les_emprunts(self) -> List[Emprunt]:
        return [self._emprunt(r) for r in self.conn.execute("SELECT * FROM emprunts ORDER BY id")]

    def emprunts_en_retard(self, jour: date) -> List[Emprunt]:
        rows = self.conn.execute("SELECT * FROM emprunts WHERE retour_reel IS NULL AND retour_prevu < ? "
                                 "ORDER BY retour_prevu", (jour.isoformat(),)).fetchall()
        return [self._emprunt(r) for r in rows]

    def plus_empruntes(self, limite: int = 5):
        rows = self.conn.execute("SELECT l.code, l.titre, COUNT(*) AS n FROM emprunts e "
                                 "JOIN livres l ON l.code = e.code_livre GROUP BY l.code "
                                 "ORDER BY n DESC, l.code LIMIT ?", (limite,)).fetchall()
        return [(r["code"], r["titre"], r["n"]) for r in rows]

    # ---------- réservations ----------
    def creer_reservation(self, code: str, matricule: str, jour: date):
        self.conn.execute("INSERT INTO reservations (code_livre, matricule, date_reservation) VALUES (?,?,?)",
                          (code, matricule, jour.isoformat()))
        self.conn.commit()

    def reservations_actives(self, code: str) -> List[Reservation]:
        rows = self.conn.execute("SELECT * FROM reservations WHERE code_livre=? AND active=1 ORDER BY id",
                                 (code,)).fetchall()
        return [self._resa(r) for r in rows]

    def desactiver_reservation(self, resa_id: int):
        self.conn.execute("UPDATE reservations SET active=0 WHERE id=?", (resa_id,))
        self.conn.commit()

    # ---------- amendes ----------
    def creer_amende(self, matricule: str, emprunt_id: int, montant: int):
        self.conn.execute("INSERT INTO amendes (matricule, emprunt_id, montant) VALUES (?,?,?)",
                          (matricule, emprunt_id, montant))
        self.conn.commit()

    def amendes_impayees(self, matricule: str) -> int:
        return self.conn.execute("SELECT COALESCE(SUM(montant),0) FROM amendes WHERE matricule=? AND payee=0",
                                 (matricule,)).fetchone()[0]

    def payer_amendes(self, matricule: str):
        self.conn.execute("UPDATE amendes SET payee=1 WHERE matricule=?", (matricule,))
        self.conn.commit()
