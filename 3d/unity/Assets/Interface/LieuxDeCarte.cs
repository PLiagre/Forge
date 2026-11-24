using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
namespace Forge.Interface
{
    // Lecture des lieux des cellules tenues par le joueur, hors du fil principal ; rien n'est posé sur la carte : chaque lieu a déjà sa forme et la couleur de son pays sur le terrain.
    // `EnAlerte` dit quels lieux du joueur voient partir plus de gens qu'il n'en arrive sur trente jours, en couples (cellule, rang) triés ;
    // `VersionDesAlertes` change quand cet ensemble change, et seulement alors, pour que la carte ne repeigne qu'à ce moment. `TexteLegende` relève ce qui manque. Lecture seule.
    public sealed class LieuxDeCarte : MonoBehaviour
    {
        public const string ENTETE = "Rouge : vos lieux d'où partent plus de gens qu'il n'en arrive, sur trente jours."; public const float PERIODE_S = 2f;
        public Func<long, LectureLieu> Lecteur;
        public string TexteLegende { get; private set; } public bool Peint => peinte != null; // lus par la légende du mode Politique et son infobulle ; peint, une maison du joueur est lue
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        public IReadOnlyList<(long cell, long rang)> EnAlerte { get; private set; } = new (long, long)[0]; public int VersionDesAlertes { get; private set; } // vide quand la maison change ou se vide
        public event Action<string, IReadOnlyList<(long cell, LectureLieu lieu)>> Applique; // la maison et la réponse appliquée ; maison nulle quand l'ancien domaine est vidé
        CarteDessinee carte; CabinetDeCarte cabinet; Task<Paquet> vol; double prochaine; string peinte;
        sealed class Paquet { public string Maison; public List<(long cell, LectureLieu lieu)> Cellules; }
        public void Installer() { carte = GetComponent<CarteDessinee>(); cabinet = GetComponent<CabinetDeCarte>(); TexteLegende = ENTETE; }
        // Aucun lieu ne se pose sur la carte : il n'y a ni armée ni nombre sous lesquels en cacher un.
        public void Eviter(CarteDeLaGuerre guerre, CalquesCarte calques) { }
        void Update() => Pas(Time.realtimeSinceStartupAsDouble);
        // Une terre se nomme par son bourg (le rang 0 servi), un lieu par son nom servi ; l'absence se dit, jamais un numéro.
        public static string Bourg(Lieu lieu) { var b = lieu.Bourg; return b?.Nom ?? "Bourg sans nom (" + TexteDuMonde.Absence(b == null ? "bourg non servi" : b.AbsenceDuNom, Cle(lieu)) + ")"; }
        public static string Tenue(Lieu lieu, LieuPlace place) => place.Rang == 0 ? Bourg(lieu) : Bourg(lieu) + " · " + (place.Nom ?? "lieu sans nom (" + TexteDuMonde.Absence(place.AbsenceDuNom, Cle(lieu)) + ")");
        static string Cle(Lieu lieu) => lieu.CellId.ToString(CultureInfo.InvariantCulture);
        public void Pas(double t)
        {
            string id = Maison(); if (id != peinte) { Alerter(new List<(long, long)>()); peinte = id; TexteLegende = ENTETE; Applique?.Invoke(null, null); }
            if (vol != null && vol.IsCompleted) { var fini = vol; vol = null; if (id != null && !fini.IsFaulted && fini.Result.Maison == id) Appliquer(fini.Result); }
            if (vol != null || id == null || t < prochaine || carte == null || carte.PositionSurLaCarte(default, 0f) == null) return;
            var cells = Cellules(); var lire = Lecteur ?? Lire; prochaine = t + PERIODE_S; string maison = id;
            vol = Task.Run(() => { var lus = new List<(long, LectureLieu)>(cells.Count); foreach (long c in cells) lus.Add((c, SansFaute(lire, c))); return new Paquet { Maison = maison, Cellules = lus }; });
        }
        string Maison() { var p = cabinet != null ? cabinet.Partie : null; var m = p != null ? p.Monde : null; var h = p != null ? p.Maison : null; return m == null || !m.Presente || string.IsNullOrEmpty(m.Donnees.MaisonDuJoueur) || h == null || !h.Presente || h.Donnees.Id != m.Donnees.MaisonDuJoueur ? null : h.Donnees.Id; }
        List<long> Cellules() { var vus = new HashSet<long>(); var liste = new List<long>(); foreach (var t in cabinet.Partie.Maison.Donnees.Lieux) if (vus.Add(t.CellId)) liste.Add(t.CellId); return liste; }
        LectureLieu Lire(long cell) { using (var c = new ClientLieu(carte.port, ClientDeparts.DelaiMinimal)) return c.Lire(cell); }
        static LectureLieu SansFaute(Func<long, LectureLieu> lire, long cell) { try { return lire(cell); } catch (Exception e) { return LectureLieu.Absent("lieu " + cell.ToString(CultureInfo.InvariantCulture) + " : " + e.GetBaseException().Message); } }
        // Un lieu sans flux servi n'est pas en alerte : son absence se dit dans le relevé.
        void Appliquer(Paquet p)
        {
            var sb = new StringBuilder(ENTETE); var alertes = new List<(long cell, long rang)>();
            foreach (var (cell, lu) in p.Cellules)
            {
                string c = cell.ToString(CultureInfo.InvariantCulture);
                if (!lu.Presente || lu.Lieu.Lieux == null || lu.Lieu.Lieux.Count == 0) { sb.Append("\nTerre sans lieux lus : ").Append(TexteDuMonde.Absence(!lu.Presente ? lu.Absence : lu.Lieu.Lieux == null ? lu.Lieu.AbsenceDesLieux ?? "lieux non servis" : "liste vide", c)); continue; }
                sb.Append('\n').Append(Bourg(lu.Lieu)).Append(" · relevé au ").Append(TexteDuMonde.Date(new DateDuMonde(lu.Lieu.Annee, lu.Lieu.JourDeLAnnee)));
                foreach (var lieu in lu.Lieu.Lieux)
                {
                    if (lieu.Maitre == p.Maison && lieu.Flux != null && lieu.Flux.PartisPersonnes > lieu.Flux.ArrivesPersonnes) alertes.Add((cell, lieu.Rang));
                    Vector3? pose = lieu.Position is PointCarte point ? carte.PositionSurLaCarte(point, 0f) : null;
                    if (pose == null || lieu.Maitre == null) { sb.Append('\n').Append(Tenue(lu.Lieu, lieu)).Append(pose == null ? " : point absent" : " : maître absent"); continue; }
                    if (lieu.Flux == null) sb.Append('\n').Append(Tenue(lu.Lieu, lieu)).Append(" : ").Append(TexteDuMonde.Absence(lieu.AbsenceDesFlux ?? "flux non servis", c));
                }
            }
            Alerter(alertes); TexteLegende = sb.ToString(); Applique?.Invoke(p.Maison, p.Cellules);
        }
        // L'ensemble trié des lieux en alerte ; sa version ne bouge que s'il a changé.
        void Alerter(List<(long cell, long rang)> alertes)
        {
            alertes.Sort(); if (alertes.SequenceEqual(EnAlerte)) return;
            EnAlerte = alertes; VersionDesAlertes++;
        }
    }
}
