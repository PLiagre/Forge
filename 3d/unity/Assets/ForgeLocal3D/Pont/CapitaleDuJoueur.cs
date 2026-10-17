using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
namespace Forge.Pont
{
    // Les terres qui ont un kit 3D : un fait de la vue, pas du monde. Clé : l'identifiant de maison servi ; valeur : la scène de sa capitale.
    public static class TerresAvecKit
    {
        public static IReadOnlyDictionary<string, string> Scenes { get; } =
            new ReadOnlyDictionary<string, string>(new Dictionary<string, string> { ["seigneurie-6"] = "Forge_Desert_Ville_ksar_des_sept_puits" });
    }
    public enum DestinationDeCapitale { Depart, Ville, PasDeKit }
    // Où mener le joueur. Maison nulle pour Depart ; Scene et Cellule renseignées seulement pour Ville.
    public sealed class CapitaleAOuvrir
    {
        public DestinationDeCapitale Destination { get; } public string Maison { get; } public string Scene { get; } public long? Cellule { get; }
        CapitaleAOuvrir(DestinationDeCapitale destination, string maison, string scene, long? cellule) { Destination = destination; Maison = maison; Scene = scene; Cellule = cellule; }
        internal static CapitaleAOuvrir AuDepart() => new CapitaleAOuvrir(DestinationDeCapitale.Depart, null, null, null);
        internal static CapitaleAOuvrir SansKit(string maison) => new CapitaleAOuvrir(DestinationDeCapitale.PasDeKit, maison, null, null);
        internal static CapitaleAOuvrir EnVille(string maison, string scene, long cellule) => new CapitaleAOuvrir(DestinationDeCapitale.Ville, maison, scene, cellule);
    }
    // Lit GET /monde, puis GET /maison?id= seulement pour une terre qui a un kit. La cellule est celle du siège servi.
    // Une absence garde la cause de son client (« monde : », « maison : ») : jamais une destination de remplacement.
    public static class AiguillageDeCapitale
    {
        public static Lecture<CapitaleAOuvrir> Lire(int port, TimeSpan delai)
        {
            // Les deux clients refusent le port et le délai avant toute requête.
            using (var monde = new ClientMonde(port, delai))
            using (var fiches = new ClientMaison(port, delai))
            {
                var lu = monde.LireAvecMaison();
                if (!lu.Presente) return Lecture<CapitaleAOuvrir>.Absent(lu.Absence);
                string maison = lu.Donnees.MaisonDuJoueur;
                if (maison == null) return Lecture<CapitaleAOuvrir>.De(CapitaleAOuvrir.AuDepart());
                if (!TerresAvecKit.Scenes.TryGetValue(maison, out string scene)) return Lecture<CapitaleAOuvrir>.De(CapitaleAOuvrir.SansKit(maison));
                var fiche = fiches.Lire(maison);
                if (!fiche.Presente) return Lecture<CapitaleAOuvrir>.Absent(fiche.Absence);
                long? cellule = fiche.Donnees.Siege.CellId;
                if (cellule == null) return Lecture<CapitaleAOuvrir>.Absent("maison : siège de " + maison + " sans cellule (" + fiche.Donnees.Absents["siege"] + ")");
                return Lecture<CapitaleAOuvrir>.De(CapitaleAOuvrir.EnVille(maison, scene, cellule.Value));
            }
        }
    }
}
