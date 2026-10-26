using System;
namespace Forge.Pont
{
    // Lot #687 : sur quoi le jeu s'ouvre au lancement. LaisseeALaCarte : -forgeCarte, déjà traité par OuvertureDeLaCarte.
    public enum ModeDOuverture { Ville, Carte, LaisseeALaCarte }
    // Cellule renseignée seulement pour Ville ; Scene égale à OuvertureDeLaCarte.SCENE seulement pour Carte.
    public sealed class OuvertureDecidee
    {
        public ModeDOuverture Mode { get; } public long? Cellule { get; } public string Scene { get; }
        OuvertureDecidee(ModeDOuverture mode, long? cellule, string scene) { Mode = mode; Cellule = cellule; Scene = scene; }
        internal static OuvertureDecidee EnVille(long cellule) => new OuvertureDecidee(ModeDOuverture.Ville, cellule, null);
        internal static OuvertureDecidee ALaCarte() => new OuvertureDecidee(ModeDOuverture.Carte, null, OuvertureDeLaCarte.SCENE);
        internal static OuvertureDecidee LaisseeALaCarte() => new OuvertureDecidee(ModeDOuverture.LaisseeALaCarte, null, null);
    }
    // Décision pure : tout vient des paramètres. Dans l'ordre : la remise (#701), -forgeCarte, -forgeCell, l'éditeur (le ksar de 1175),
    // enfin l'aiguillage de #679, consulté une seule fois. Une absence garde sa cause : jamais une cellule de remplacement.
    public static class OuvertureDeLaCapitale
    {
        public static Lecture<OuvertureDecidee> Decider(string[] arguments, bool editeur, Func<Lecture<CapitaleAOuvrir>> aiguillage)
            => Decider(arguments, editeur, null, aiguillage);
        // Lot #701 : la cellule remise par le passage de la carte (PassageALaCapitale) passe avant tout, sans lire l'aiguillage.
        public static Lecture<OuvertureDecidee> Decider(string[] arguments, bool editeur, long? remise, Func<Lecture<CapitaleAOuvrir>> aiguillage)
        {
            if (arguments == null) throw new ArgumentNullException(nameof(arguments));
            if (aiguillage == null) throw new ArgumentNullException(nameof(aiguillage));
            if (remise < 0) throw new ArgumentOutOfRangeException(nameof(remise), remise, "un cell_id entier positif ou nul attendu");
            if (remise != null) return Lecture<OuvertureDecidee>.De(OuvertureDecidee.EnVille(remise.Value));
            if (OuvertureDeLaCarte.Demandee(arguments)) return Lecture<OuvertureDecidee>.De(OuvertureDecidee.LaisseeALaCarte());
            if (Array.IndexOf(arguments, PanneauLieu.ARGUMENT_CELLULE) >= 0)
            {
                long cellule = PanneauLieu.LireCellule(arguments, PanneauLieu.CELLULE_PAR_DEFAUT, out string erreur);
                return erreur != null ? Lecture<OuvertureDecidee>.Absent(erreur) : Lecture<OuvertureDecidee>.De(OuvertureDecidee.EnVille(cellule));
            }
            if (editeur) return Lecture<OuvertureDecidee>.De(OuvertureDecidee.EnVille(PanneauLieu.CELLULE_PAR_DEFAUT));
            var lue = aiguillage() ?? throw new InvalidOperationException("l'aiguillage n'a rendu aucune lecture");
            if (!lue.Presente) return Lecture<OuvertureDecidee>.Absent(lue.Absence);
            var capitale = lue.Donnees;
            return Lecture<OuvertureDecidee>.De(capitale.Destination == DestinationDeCapitale.Ville
                ? OuvertureDecidee.EnVille(capitale.Cellule ?? throw new InvalidOperationException("une capitale en ville sans cellule"))
                : OuvertureDecidee.ALaCarte());
        }
    }
}
