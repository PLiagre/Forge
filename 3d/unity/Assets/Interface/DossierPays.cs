using System;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using UnityEngine;

namespace Forge.Interface
{
    // Lot #1045 : le feuillet « Le pays ». Il écrit ce que `GET /pays` sert au tick du monde lu : les lieux du joueur, son suzerain et ses vassaux, ses gens,
    // sa récolte, ses greniers, ses chantiers et ses bâtiments. Les noms viennent de `/maisons` et de `NomsDesTerres`, jamais de `/pays`.
    public sealed class DossierPays : MonoBehaviour
    {
        public const string TITRE = "Le pays", ICONE = "Le pays";
        const string NON_NOMMEE = "maison non nommée", ABSENTE = "maison absente du registre";
        Feuillet feuillet;
        Func<Lecture<MondeAvecMaisonLu>> monde;
        Func<Lecture<TerresDuPays>> terres;
        LectureDossier registre;
        NomsDesTerres noms;
        double prochaine;
        bool etaitOuvert;
        DocumentDuMonde registreCalcule;
        Lecture<IReadOnlyDictionary<string, string>> registreLu;
        public string TexteAffiche { get; private set; }
        public RectTransform Cadre => feuillet.Cadre;

        public void Initialiser(Transform toile, Transform barre, Func<Lecture<MondeAvecMaisonLu>> monde, Func<Lecture<TerresDuPays>> terres, LectureDossier registre, NomsDesTerres noms)
        {
            this.monde = monde; this.terres = terres; this.registre = registre; this.noms = noms;
            feuillet = gameObject.AddComponent<Feuillet>(); feuillet.Initialiser(toile, TITRE);
            Action bascule = () => { if (feuillet.Ouvert) feuillet.Fermer(); else feuillet.Ouvrir(); };
            EmblemeCommande.Icone(barre, ICONE, 0, bascule, "Le pays : ouvre ou ferme le feuillet de votre pays : ses lieux, ses vassaux, ses gens, son grain et ses bâtiments.");
        }
        void LateUpdate() => Pas(Time.realtimeSinceStartupAsDouble);
        void OnDestroy() => registre?.Vider();
        void Ecrire(string texte) { TexteAffiche = texte; feuillet.Ecrire(texte); }

        public void Pas(double maintenant)
        {
            if (feuillet == null || !feuillet.Ouvert) { etaitOuvert = false; return; }
            var lueDuMonde = monde(); var lueDesTerres = terres();
            if (!etaitOuvert) { etaitOuvert = true; Relire(maintenant); } // chaque ouverture relit les noms, sans attendre
            var lu = LireLeRegistre();
            if (maintenant >= prochaine && (lu == null || !lu.Presente || Manque(lueDuMonde, lueDesTerres, lu.Donnees))) Relire(maintenant);
            Ecrire(Decrire(lueDuMonde, lueDesTerres, lu, (c, r) => DossierMaison.NomDuLieu(noms, c, r, maintenant)));
        }
        // Jamais pendant qu'une lecture est en cours.
        void Relire(double maintenant)
        {
            if (registre.EnCours) return;
            prochaine = maintenant + 2;
            _ = registre.Actualiser("/maisons");
        }
        // Nul tant qu'aucun document n'est lu ; absent, avec sa raison, si la lecture est en erreur ou si le document est faux.
        Lecture<IReadOnlyDictionary<string, string>> LireLeRegistre()
        {
            if (registre.Erreur != null) return Lecture<IReadOnlyDictionary<string, string>>.Absent(registre.Erreur);
            var document = registre.Document;
            if (document == null) return null;
            if (!ReferenceEquals(document, registreCalcule))
            {
                registreCalcule = document;
                try { registreLu = Lecture<IReadOnlyDictionary<string, string>>.De(Registre(document)); }
                catch (Exception e) { registreLu = Lecture<IReadOnlyDictionary<string, string>>.Absent(e.Message); }
            }
            return registreLu;
        }
        // Une maison à nommer, parmi celles du pays lu au tick du monde, manque-t-elle au registre ?
        static bool Manque(Lecture<MondeAvecMaisonLu> monde, Lecture<TerresDuPays> terres, IReadOnlyDictionary<string, string> registre)
        {
            if (!Attendu(monde, terres)) return false;
            var t = terres.Donnees;
            return ANommer(t).Any(id => !registre.ContainsKey(id));
        }
        static IEnumerable<string> ANommer(TerresDuPays t) =>
            new[] { t.MaisonId }.Concat(t.Suzerain == null ? new string[0] : new[] { t.Suzerain }).Concat(t.VassauxTous).Concat(t.Batiments.Select(b => b.Maison));
        // Les terres lues sont celles de la maison du joueur, au tick du monde lu.
        static bool Attendu(Lecture<MondeAvecMaisonLu> monde, Lecture<TerresDuPays> terres) =>
            monde != null && monde.Presente && monde.Donnees.MaisonDuJoueur != null && terres != null && terres.Presente
            && terres.Donnees.MaisonId == monde.Donnees.MaisonDuJoueur && terres.Donnees.Tick == monde.Donnees.Monde.Tick;

        public static Dictionary<string, string> Registre(DocumentDuMonde document)
        {
            var liste = DocumentDuMonde.Tableau(document.Champs, "maisons");
            if (liste.Count == 0 || liste.Count != DocumentDuMonde.Entier(document.Champs, "nombre")) throw new ArgumentException("Registre des maisons incomplet");
            var registre = new Dictionary<string, string>(liste.Count);
            foreach (var brut in liste)
            {
                var maison = brut as Dictionary<string, object> ?? throw new ArgumentException("Maison du registre invalide");
                string id = DocumentDuMonde.Texte(maison, "id");
                if (string.IsNullOrWhiteSpace(id)) throw new ArgumentException("Identifiant de maison vide dans le registre");
                object nom = DocumentDuMonde.Valeur(maison, "nom");
                if (nom != null && !(nom is string)) throw new ArgumentException("Nom de maison invalide dans le registre");
                if (!registre.TryAdd(id, (string)nom)) throw new ArgumentException("Maison répétée dans le registre");
            }
            return registre;
        }

        public static string Decrire(Lecture<MondeAvecMaisonLu> monde, Lecture<TerresDuPays> terres, Lecture<IReadOnlyDictionary<string, string>> registre, Func<long, long, string> nomDuLieu)
        {
            if (nomDuLieu == null) throw new ArgumentNullException(nameof(nomDuLieu));
            if (monde == null) return "Lecture du pays…";
            if (!monde.Presente) return "Pays indisponible : " + TexteDuMonde.Absence(monde.Absence);
            string id = monde.Donnees.MaisonDuJoueur;
            if (id == null) return "Choisissez une maison pour lire son pays.";
            if (terres == null || terres.Presente && (terres.Donnees.MaisonId != id || terres.Donnees.Tick != monde.Donnees.Monde.Tick)) return "Pays en attente du monde";
            if (!terres.Presente) return "Pays indisponible : " + TexteDuMonde.Absence(terres.Absence, id);
            if (registre == null) return "Lecture des noms des maisons…";
            if (!registre.Presente) return "Pays indisponible : " + TexteDuMonde.Absence(registre.Absence);
            return Pays(terres.Donnees, registre.Donnees, nomDuLieu);
        }

        static string Pays(TerresDuPays t, IReadOnlyDictionary<string, string> registre, Func<long, long, string> nomDuLieu)
        {
            string Maison(string id) => registre.TryGetValue(id, out string nom) ? nom ?? NON_NOMMEE : ABSENTE;
            var l = new List<string>
            {
                Maison(t.MaisonId) + " · relevé au " + TexteDuMonde.Date(t.Date),
                "Suzerain : " + (t.Suzerain == null ? "aucun" : Maison(t.Suzerain)),
                "Vassaux : " + (t.Vassaux.Count == 0 ? "aucun" : Compte(t.Vassaux.Count, "maison", "maisons")),
                "", "GENS ET GRAIN",
                "Lieux : " + Compte(t.NombreDeLieux, "lieu", "lieux") + ", dont " + Compte(t.Lieux.Count, "lieu tenu", "lieux tenus") + " en propre",
                "Habitants : " + Compte(t.Habitants, "habitant", "habitants") + ", dont " + Compte(t.HabitantsPropres, "habitant", "habitants") + " sur ses propres lieux",
                "Récolte des trente derniers jours : " + TexteDuMonde.Masse(t.Recolte30jKg) + " de grain",
                "Grenier : " + (t.GrenierKg == null ? TexteDuMonde.Absence(t.AbsenceDuGrenier, t.MaisonId) : TexteDuMonde.Masse(t.GrenierKg.Value) + " de vivres"),
                "Greniers des vassaux : " + TexteDuMonde.Masse(t.GreniersDesVassauxKg) + " de vivres",
                "Chantiers des bourgs : " + Compte(t.Chantiers, "chantier", "chantiers") + " en cours",
                "", "BÂTIMENTS"
            };
            if (t.Batiments.Count == 0) l.Add("aucun");
            foreach (var b in t.Batiments)
                l.Add(b.Nom + " à " + nomDuLieu(b.CellId, 0) + (b.Maison == t.MaisonId ? "" : ", de " + Maison(b.Maison)) + " : "
                    + (b.EnChantier ? "en chantier, " + TexteDuMonde.Jours(b.TravailFourni) + " de travail sur " + TexteDuMonde.Jours(b.TravailRequis) : "achevé"));
            l.Add(""); l.Add("SES LIEUX"); l.AddRange(Terres(t.Lieux, nomDuLieu));
            l.Add(""); l.Add("SES VASSAUX");
            l.Add(t.Vassaux.Count == 0 ? "aucun" : string.Join(", ", t.Vassaux.Select(Maison)));
            var autres = t.VassauxTous.Where(v => !t.Vassaux.Contains(v)).ToList();
            if (autres.Count > 0) l.Add("Par leurs vassaux (" + Compte(autres.Count, "maison", "maisons") + ") : " + string.Join(", ", autres.Select(Maison)));
            l.Add(""); l.Add("LIEUX DE SES VASSAUX"); l.AddRange(Terres(t.LieuxDesVassaux, nomDuLieu));
            return string.Join("\n", l);
        }

        // Une ligne par terre, dans l'ordre de leur première apparition ; dans une terre, les lieux suivent l'ordre des rangs.
        static IEnumerable<string> Terres(IReadOnlyList<LieuDuPays> lieux, Func<long, long, string> nomDuLieu)
        {
            if (lieux.Count == 0) { yield return "aucun"; yield break; }
            foreach (var terre in lieux.GroupBy(x => x.CellId))
            {
                long cell = terre.Key; string bourg = nomDuLieu(cell, 0);
                bool tenu = terre.Any(x => x.Rang == 0);
                var autres = terre.Where(x => x.Rang != 0).OrderBy(x => x.Rang).Select(x => nomDuLieu(cell, x.Rang)).ToList();
                if (!tenu) yield return "Autour de " + bourg + " : " + string.Join(", ", autres);
                else if (autres.Count == 0) yield return bourg;
                else yield return bourg + " et " + Compte(autres.Count, "lieu", "lieux") + " : " + string.Join(", ", autres);
            }
        }
        // Un compte s'accorde au pluriel au-delà de 1 (« 0 lieu », « 1 lieu », « 2 lieux »), comme `TexteDuMonde.Jours`.
        static string Compte(long n, string singulier, string pluriel) => TexteDuMonde.Nombre(n) + " " + (n > 1 ? pluriel : singulier);
    }
}
