using System;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Lot #1032 : sous la barre des comptes, la ligne des trois jauges et des trois réserves de points du pays, lues sur `/pays` au tick du monde lu.
    // Une classe simple : le cabinet l'appelle à chaque image. Chaque cellule dit sa valeur, ce que gagne une réserve par mois, le sens de la dernière
    // variation vue (en mots, sans la couleur), et porte une infobulle qui dit d'où vient la valeur. La barre ne compare que deux valeurs servies.
    public sealed class BarreDuPays
    {
        public const string NOM = "Jauges du pays";
        const string ATTENTE = "Jauges en attente du monde", BAISSE = ", en baisse", HAUSSE = ", en hausse";
        const float LARGEUR = 1872, HAUTEUR = 26;
        // Les clés servies par `/pays` et les noms des cellules : les trois jauges, puis les trois réserves.
        static readonly string[] CLES = { "concorde", "renom", "droit", "plume", "sceau", "epee" };
        static readonly string[] CELLULES = { "Concorde", "Renom", "Droit", "Plume", "Sceau", "Épée" };
        static readonly float[] X = { 0, 240, 480, 720, 1104, 1488 }, LARGEURS = { 240, 240, 240, 384, 384, 384 };
        // Posé à la main : la culture `fr-FR` du système n'écrit pas toujours le même signe moins.
        static readonly NumberFormatInfo Fr = NumberFormatInfo.ReadOnly(new NumberFormatInfo { NumberDecimalSeparator = ",", NegativeSign = "-" });

        // Le dernier changement vu d'une valeur : son sens, son avant, son après, et la date de la lecture qui l'a vu.
        sealed class Retenu { public bool Baisse; public double Avant, Apres; public DateDuMonde Date; }

        readonly RectTransform conteneur;
        readonly Text etat;
        readonly Text[] cellules = new Text[CLES.Length];
        readonly Infobulle[] bulles = new Infobulle[CLES.Length];
        // La dernière lecture faite à un tick plus grand que la précédente, pour la maison montrée.
        string vueMaison; long vueTick; double[] vues; Retenu[] retenus = new Retenu[CLES.Length];

        public BarreDuPays(RectTransform bandeau)
        {
            conteneur = new GameObject(NOM, typeof(RectTransform)).GetComponent<RectTransform>();
            conteneur.SetParent(bandeau, false);
            conteneur.anchorMin = conteneur.anchorMax = conteneur.pivot = new Vector2(0, 1);
            conteneur.anchoredPosition = new Vector2(24, -98); conteneur.sizeDelta = new Vector2(LARGEUR, HAUTEUR);
            etat = Texte("Lecture du pays…", 0, LARGEUR);
            etat.name = "État du pays";
            for (int i = 0; i < CLES.Length; i++)
            {
                var cellule = Texte(CELLULES[i], X[i], LARGEURS[i]);
                cellule.name = CELLULES[i]; cellule.raycastTarget = true; // l'infobulle se lit au survol
                cellules[i] = cellule; bulles[i] = cellule.gameObject.AddComponent<Infobulle>();
            }
            Activer(false, null);
        }

        Text Texte(string contenu, float x, float largeur)
        {
            var texte = SocleInterface.Texte(conteneur, contenu, x, 0, largeur, taille: 16);
            texte.color = SocleInterface.Couleur("papier"); texte.supportRichText = false;
            texte.rectTransform.sizeDelta = new Vector2(largeur, HAUTEUR);
            return texte;
        }

        // Dans l'ordre de `CabinetDeCarte.Barre` : le monde d'abord, puis la maison, puis le pays au même tick.
        public void Afficher(Lecture<MondeAvecMaisonLu> monde, Lecture<PaysLu> pays)
        {
            if (pays != null && pays.Presente) Noter(pays.Donnees);
            if (monde == null) { Activer(true, "Lecture du pays…"); return; }
            if (!monde.Presente) { Activer(true, "Pays indisponible : " + TexteDuMonde.Absence(monde.Absence)); return; }
            string id = monde.Donnees.MaisonDuJoueur;
            if (id == null) { Activer(false, null); return; }
            if (pays == null || pays.Presente && (pays.Donnees.MaisonId != id || pays.Donnees.Tick != monde.Donnees.Monde.Tick)) { Activer(true, ATTENTE); return; }
            if (!pays.Presente) { Activer(true, "Jauges indisponibles : " + TexteDuMonde.Absence(pays.Absence, id)); return; }
            var lu = pays.Donnees;
            for (int i = 0; i < CLES.Length; i++)
                if (!(i < 3 ? lu.Jauges.ContainsKey(CLES[i]) : lu.Points.ContainsKey(CLES[i])))
                { Activer(true, "Jauges indisponibles : " + CELLULES[i] + " non servie par le monde"); return; }
            for (int i = 0; i < CLES.Length; i++)
            {
                var (texte, phrase) = i < 3 ? Jauge(lu, i) : Reserve(lu, i, id);
                cellules[i].text = texte; bulles[i].phrase = phrase;
            }
            etat.gameObject.SetActive(false);
            foreach (var cellule in cellules) cellule.gameObject.SetActive(true);
        }

        // L'état dit pourquoi les cellules sont absentes : `texte` nul, il se tait ; les cellules ne s'allument qu'à la fin d'`Afficher`.
        void Activer(bool etatActif, string texte)
        {
            etat.gameObject.SetActive(etatActif);
            if (texte != null) etat.text = texte;
            for (int i = 0; i < cellules.Length; i++) { cellules[i].gameObject.SetActive(false); cellules[i].text = ""; bulles[i].phrase = ""; } // aucun nombre d'une lecture périmée
        }

        // Compare une lecture à celle d'avant : un changement est retenu avec son sens ; une autre maison ou un tick plus petit efface tout.
        void Noter(PaysLu lu)
        {
            if (!CLES.Select((c, i) => i < 3 ? lu.Jauges.ContainsKey(c) : lu.Points.ContainsKey(c)).All(servie => servie)) return;
            if (vues != null && lu.MaisonId == vueMaison && lu.Tick == vueTick) return;
            var valeurs = CLES.Select((c, i) => i < 3 ? lu.Jauges[c].Valeur : lu.Points[c].Valeur).ToArray();
            if (vues == null || lu.MaisonId != vueMaison || lu.Tick < vueTick) retenus = new Retenu[CLES.Length];
            else for (int i = 0; i < CLES.Length; i++)
                if (valeurs[i] != vues[i]) retenus[i] = new Retenu { Baisse = valeurs[i] < vues[i], Avant = vues[i], Apres = valeurs[i], Date = lu.Date };
            vueMaison = lu.MaisonId; vueTick = lu.Tick; vues = valeurs;
        }

        string Sens(int i) => retenus[i] == null ? "" : retenus[i].Baisse ? BAISSE : HAUSSE;

        string Fin(PaysLu lu, int i)
        {
            var r = retenus[i];
            string sens = r == null ? "" : (r.Baisse ? "En baisse" : "En hausse") + " depuis le " + TexteDuMonde.Date(r.Date) + " : de " + TexteDuMonde.Points(r.Avant) + " à " + TexteDuMonde.Points(r.Apres) + ".\n";
            return sens + "Relevé au " + TexteDuMonde.Date(lu.Date) + ".";
        }

        (string, string) Jauge(PaysLu lu, int i)
        {
            var j = lu.Jauges[CLES[i]];
            string phrase = j.Nom + " : " + j.Dit + ". " + TexteDuMonde.Points(j.Valeur) + ", de " + TexteDuMonde.Points(j.Minimum) + " à " + TexteDuMonde.Points(j.Maximum)
                + ", neutre à " + TexteDuMonde.Points(j.Neutre) + ".";
            var poses = lu.Poses.Where(p => p.Jauge == CLES[i]).Select(p => "Pose au pays : " + p.NomDeLaGrandeur + " " + (p.Valeur > 0 ? "+" : "")
                + (p.Valeur * 100).ToString("0.##", Fr) + " %.").ToArray();
            phrase += "\n" + (poses.Length > 0 ? string.Join("\n", poses) : "À son neutre, elle ne pose rien.") + "\n" + Fin(lu, i);
            return (j.Nom + " " + TexteDuMonde.Points(j.Valeur) + Sens(i), phrase);
        }

        (string, string) Reserve(PaysLu lu, int i, string id)
        {
            var p = lu.Points[CLES[i]];
            string phrase = p.Nom + " : " + p.Dit + ". " + TexteDuMonde.Points(p.Valeur) + ", au plus " + TexteDuMonde.Points(p.Plafond) + ".\n", texte = p.Nom + " " + TexteDuMonde.Points(p.Valeur);
            if (lu.Competences == null || p.ParMois == null)
            {
                phrase += "Le monde ne connaît pas le chef de cette maison : ce qu'elle gagne par mois est absent, pas nul (" + TexteDuMonde.Absence(lu.SansChef ?? "chef non connu", id) + ").";
                texte += ", chef non connu";
            }
            else
            {
                phrase += "Gagne " + TexteDuMonde.Points(p.ParMois.Value) + " par mois : la " + p.Domaine + " du chef, " + TexteDuMonde.Points(lu.Competences[p.Domaine]) + ".";
                texte += ", +" + TexteDuMonde.Points(p.ParMois.Value) + "/mois";
            }
            return (texte + Sens(i), phrase + "\n" + Fin(lu, i));
        }
    }
}
