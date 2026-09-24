using Unity.Entities;
using Unity.Mathematics;
using Unity.Rendering;

namespace Guerre
{
    // Un soldat est une personne : son numéro dans le régiment, son élan, son pas.
    // Le régiment ne marche pas à sa place, il lui dit seulement où se tenir.
    public struct Soldat : IComponentData
    {
        public Entity Regiment;
        public int Numero;       // rang d'appel dans le régiment : sa place se déduit de la formation
        public float2 Decalage;  // quelques centimètres : personne ne se tient au cordeau
        public float2 Vitesse;   // m/s, dans le plan
        public float Phase;      // cycles de marche accomplis : un cycle vaut deux pas
        public float Allure;     // 0,9 à 1,1 : tous les hommes ne marchent pas au même train
        public float Ecart;      // distance à sa place, en mètres, à la dernière image
        public float3 Teinte;
    }

    // L'état d'animation lu par le shader du soldat, instance par instance :
    // x phase de marche (0..1), y poids de la marche, z décalage du repos.
    [MaterialProperty("_AnimEtat")]
    public struct AnimEtat : IComponentData
    {
        public float4 Value;
    }

    // L'ordre donné à des hommes : un point, une direction, une largeur de front.
    public struct Regiment : IComponentData
    {
        public float2 Position;      // l'ancre de la formation, qui avance vers la cible
        public float2 Cible;
        public float2 Front;         // direction vers laquelle la formation fait face (unitaire)
        public float2 FrontCible;
        public float2 Base, Avant;   // les deux lignes du scénario de démonstration
        public float VitesseMarche;
        public float Espacement;
        public float Attente;
        public float Ecart;          // écart moyen de ses hommes à leur place
        public int Files;            // largeur du front, en hommes
        public int Effectif;
        public int Index;
        public int Arme;             // 0 piquiers, 1 hallebardiers, 2 arbalétriers
        public int Camp;
        public int Etape;
        public byte Ordonne;         // 1 : le joueur a pris la main, le scénario s'arrête
        public byte Selection;

        public int Rangs => (Effectif + Files - 1) / Files;
        public float Largeur => (math.min(Files, Effectif) - 1) * Espacement;
        public float Profondeur => (Rangs - 1) * Espacement;
    }

    // Réglages de la simulation. Corps = 0 retire la gêne entre les hommes :
    // c'est la contre-épreuve des essais, jamais un réglage de jeu.
    public struct ReglagesSimulation : IComponentData
    {
        public byte Corps;
    }

    public static class Formation
    {
        // Place d'un homme dans le repère du régiment : x vers la droite, y vers l'avant.
        // Le dernier rang, incomplet, se centre derrière les autres.
        public static float2 Place(in Regiment r, int numero)
        {
            int files = math.max(1, math.min(r.Files, r.Effectif));
            int rangs = (r.Effectif + files - 1) / files;
            int rg = numero / files, f = numero % files;
            int dansLeRang = rg == rangs - 1 ? r.Effectif - rg * files : files;
            return new float2((f - (dansLeRang - 1) / 2f) * r.Espacement, -(rg - (rangs - 1) / 2f) * r.Espacement);
        }

        public static float2 VersMonde(float2 local, float2 ancre, float2 front)
        {
            float2 droite = new float2(front.y, -front.x);
            return ancre + droite * local.x + front * local.y;
        }
    }

    // Le relief lu une fois depuis le Terrain, pour poser les pieds dans les jobs Burst.
    public struct ReliefBlob
    {
        public BlobArray<float> Hauteurs; // [z * Resolution + x], en mètres
        public int Resolution;
        public float Taille;
        public float3 Origine;
    }

    public struct Relief : IComponentData
    {
        public BlobAssetReference<ReliefBlob> Blob;
    }

    public static class Sol
    {
        // Le Terrain de Unity découpe chaque maille le long de la diagonale
        // (i,j)–(i+1,j+1) : on suit le même découpage pour que les pieds
        // touchent exactement la surface dessinée.
        public static float Hauteur(ref ReliefBlob r, float2 p)
        {
            int n = r.Resolution;
            float2 uv = (p - r.Origine.xz) / r.Taille * (n - 1);
            uv = math.clamp(uv, 0f, n - 1.0001f);
            int2 i = (int2)math.floor(uv);
            float2 f = uv - i;
            float h00 = r.Hauteurs[i.y * n + i.x];
            float h10 = r.Hauteurs[i.y * n + i.x + 1];
            float h01 = r.Hauteurs[(i.y + 1) * n + i.x];
            float h11 = r.Hauteurs[(i.y + 1) * n + i.x + 1];
            float h = f.x >= f.y
                ? h00 + (h10 - h00) * f.x + (h11 - h10) * f.y
                : h00 + (h11 - h01) * f.x + (h01 - h00) * f.y;
            return r.Origine.y + h;
        }
    }
}
