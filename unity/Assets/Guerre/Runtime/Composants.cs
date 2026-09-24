using Unity.Entities;
using Unity.Mathematics;

namespace Guerre
{
    // Un soldat est une personne : sa place dans le rang, son élan, son pas.
    // Le régiment ne marche pas à sa place, il lui dit seulement où se tenir.
    public struct Soldat : IComponentData
    {
        public Entity Regiment;
        public float2 Place;     // décalage dans le rang : x vers la droite, y vers l'avant
        public float2 Vitesse;   // m/s, dans le plan
        public float Phase;      // cycle du pas
        public float Allure;     // 0,9 à 1,1 : tous les hommes ne marchent pas au même train
        public float3 Teinte;
    }

    // L'ordre donné à des hommes : un point, une direction, une allure.
    public struct Regiment : IComponentData
    {
        public float2 Position;      // l'ancre de la formation, qui avance vers la cible
        public float2 Cible;
        public float2 Front;         // direction vers laquelle la formation fait face (unitaire)
        public float2 FrontCible;
        public float2 Base, Avant;   // les deux lignes du scénario de démonstration
        public float VitesseMarche;
        public float Attente;
        public int Camp;
        public int Etape;
        public byte Ordonne;         // 1 : le joueur a pris la main, le scénario s'arrête
        public byte Selection;
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
