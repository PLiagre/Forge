using System;
using UnityEngine;

namespace Forge.Pont
{
    // Une pièce du kit, ou une absence qui nomme sa cause : jamais les deux.
    public sealed class PieceDuKit
    {
        public bool Presente { get; }
        public GameObject Prefab { get; }
        public string Absence { get; }

        private PieceDuKit(bool presente, GameObject prefab, string absence)
        {
            Presente = presente;
            Prefab = prefab;
            Absence = absence;
        }

        public static PieceDuKit De(GameObject prefab) =>
            new PieceDuKit(true, prefab != null ? prefab : throw new ArgumentNullException(nameof(prefab)), "");

        public static PieceDuKit Absente(string cause) =>
            new PieceDuKit(false, null, cause ?? throw new ArgumentNullException(nameof(cause)));
    }

    // Lot #368 — pour chaque nature de bâtiment, la pièce du kit du désert qui en montre chaque étape.
    // L'asset vit sous `Desert/Resources/` pour être chargé hors de l'éditeur (`Resources.Load`), sans
    // passer par `AssetDatabase`. Le kit ne choisit jamais une autre pièce : une nature ou une étape
    // qu'il n'a pas est déclarée absente.
    public sealed class KitDesBatiments : ScriptableObject
    {
        [Serializable]
        public sealed class PiecesDUneNature
        {
            public string nature = "";
            public GameObject piquets, murs, fini;
        }

        public const string Ressource = "KitDesBatiments";

        public PiecesDUneNature[] natures = new PiecesDUneNature[0];

        // Nul si l'asset manque.
        public static KitDesBatiments Charger() => Resources.Load<KitDesBatiments>(Ressource);

        public PieceDuKit Piece(string nature, EtapeDuBatiment etape)
        {
            PiecesDUneNature entree = null;
            if (nature != null && natures != null)
                foreach (var n in natures)
                    if (n != null && string.Equals(n.nature, nature, StringComparison.Ordinal)) { entree = n; break; }
            if (entree == null)
                return PieceDuKit.Absente("nature sans pièce au kit : " + (nature ?? "(nulle)"));

            GameObject prefab = etape switch
            {
                EtapeDuBatiment.Piquets => entree.piquets,
                EtapeDuBatiment.Murs => entree.murs,
                EtapeDuBatiment.Fini => entree.fini,
                _ => null,
            };
            if (prefab == null)
                return PieceDuKit.Absente("pièce manquante au kit : " + nature + " " + etape.ToString().ToLowerInvariant());
            return PieceDuKit.De(prefab);
        }
    }
}
