using System;using System.Collections.Generic;using System.Globalization;using System.Linq;using System.Security.Cryptography;using System.Text;using Forge.Pont;using UnityEngine;using UnityEngine.Rendering;using Object=UnityEngine.Object;
namespace ForgeLocal3D
{
    // Lot 738 : chaque rue de la base devient un ruban de terre battue sous « Rues de 1400 », sœur de « Maisons de 1400 ».
    // Le sable n'est ni creusé ni peint : la session vierge de DesertCityRelance exige après l'ouverture les hauteurs, les
    // couches et les touffes d'une copie vierge, et une chaussée écrite dans le terrain la ferait échouer. Le ruban est posé
    // à 0,06 m au-dessus du sol lu sous chaque sommet ; redessiné après le tick, il suit le sol que le tick a changé.
    public sealed class DesertRues1400
    {
        public const float Pas=.25f,AuDessus=.06f;
        public Transform Racine{get;}
        public int Servies{get;private set;}=-1;public int Dessinees=>Racine.childCount;public int Coupees{get;private set;}public int HorsDuTerrain{get;private set;}
        public string Absence{get;private set;}public readonly List<string> Refus=new();
        // SHA-256 de la description du dernier dessin : une ligne par rue (rang, état, sommets du monde en F2).
        public string Empreinte{get;private set;}=Hacher("");
        readonly Terrain terrain;readonly TerrainLayer couche;readonly Material materiau;
        public DesertRues1400(Transform parent,Terrain terrain,TerrainLayer couche)
        {
            this.terrain=terrain;this.couche=couche;var go=new GameObject("Rues de 1400");go.transform.SetParent(parent,false);Racine=go.transform;
            var defaut=GraphicsSettings.currentRenderPipeline?GraphicsSettings.currentRenderPipeline.defaultMaterial:null;
            if(defaut)materiau=new Material(defaut){name="Chaussée de 1400"};
        }
        // Vide cette seule racine, maillages compris. Base nulle, pipeline, couche ou texture absents : l'absence, jamais « 0 dessinée ».
        public string Dessiner(BaseDuPlan @base)
        {
            for(int i=Racine.childCount-1;i>=0;i--){var e=Racine.GetChild(i).gameObject;var f=e.GetComponent<MeshFilter>();if(f&&f.sharedMesh)Object.DestroyImmediate(f.sharedMesh);Object.DestroyImmediate(e);}
            Refus.Clear();Servies=-1;Coupees=HorsDuTerrain=0;Empreinte=Hacher("");
            Absence=@base==null?"base non servie":!materiau?"pas de matériau par défaut du pipeline":!couche?"pas de couche de terre battue":!couche.diffuseTexture?"couche « "+couche.name+" » sans texture"
                :!(couche.tileSize.x>0&&couche.tileSize.y>0)?"couche « "+couche.name+" » sans taille de tuile":null;
            if(Absence!=null)return Ligne();
            var c=couche.diffuseRemapMax;materiau.mainTexture=couche.diffuseTexture;materiau.color=new Color(c.x,c.y,c.z);materiau.SetFloat("_Smoothness",couche.smoothness);
            Servies=@base.Rues.Count;var d=new StringBuilder();for(int r=0;r<Servies;r++)Une(r,@base.Rues[r],d);
            Empreinte=Hacher(d.ToString());return Ligne();
        }
        string Ligne()
        {
            string N(int v)=>v.ToString(CultureInfo.InvariantCulture);string t="Rues de 1400 : "+(Absence??N(Dessinees)+" dessinée(s) sur "+N(Servies)+", "+N(Coupees)+" coupée(s) au bord du terrain, "+N(HorsDuTerrain)+" hors du terrain");
            return Refus.Count==0?t:t+"\n"+string.Join("\n",Refus);
        }
        // Chaque segment est découpé au carré |x|, |y| ≤ taille/2 − 1 − largeur/2 (Liang-Barsky) : la chaussée tient entière sur le terrain.
        void Une(int rang,RueDeBase rue,StringBuilder d)
        {
            string nom="Rue de 1400 rang "+rang.ToString(CultureInfo.InvariantCulture);double w=rue.LargeurM,L=terrain.terrainData.size.x/2.0-1-w/2;var p=rue.Points;
            string forme=p.Count<2?"moins de deux points":!(w>0)||double.IsInfinity(w)?"largeur nulle ou non finie":Enumerable.Range(1,p.Count-1).Any(i=>p[i].X==p[i-1].X&&p[i].Y==p[i-1].Y)?"deux points confondus":null;
            if(forme!=null){Refus.Add(nom+" : "+forme);d.Append(rang).Append(" refusee\n");return;}
            var morceaux=new List<(double ax,double ay,double lx,double ly)>();bool coupee=false;
            for(int i=1;i<p.Count;i++)
            {
                double ax=p[i-1].X,ay=p[i-1].Y,dx=p[i].X-ax,dy=p[i].Y-ay,t0=0,t1=1;
                foreach(var (q,s) in new[]{(-dx,ax+L),(dx,L-ax),(-dy,ay+L),(dy,L-ay)}){if(q==0){if(s<0)t1=-1;}else if(q<0)t0=Math.Max(t0,s/q);else t1=Math.Min(t1,s/q);}
                if(t0>0||t1<1)coupee=true;if(L>0&&t1-t0>1e-9)morceaux.Add((ax+t0*dx,ay+t0*dy,(t1-t0)*dx,(t1-t0)*dy));
            }
            if(morceaux.Count==0){HorsDuTerrain++;d.Append(rang).Append(" hors\n");return;}
            if(coupee)Coupees++;var go=new GameObject(nom);go.transform.SetParent(Racine,false);var sommets=new List<Vector3>();var uv=new List<Vector2>();var tri=new List<int>();
            d.Append(rang).Append(coupee?" coupee":" dessinee");
            foreach(var (ax,ay,lx,ly) in morceaux)
            {
                // Une grille au pas de 0,25 m au plus, en long et en travers, bords compris ; bouts carrés, sans prolongement.
                double len=Math.Sqrt(lx*lx+ly*ly),nx=-ly/len,ny=lx/len;int nl=Math.Max(1,(int)Math.Ceiling(len/Pas-1e-6)),nt=Math.Max(1,(int)Math.Ceiling(w/Pas-1e-6)),b0=sommets.Count;
                for(int i=0;i<=nl;i++)for(int j=0;j<=nt;j++)
                {
                    double u=(double)i/nl,v=((double)j/nt-.5)*w;var m=new Vector3((float)-(ax+u*lx+v*nx),0,(float)-(ay+u*ly+v*ny));
                    m.y=terrain.SampleHeight(m)+terrain.transform.position.y+AuDessus;sommets.Add(go.transform.InverseTransformPoint(m));uv.Add(new Vector2(m.x/couche.tileSize.x,m.z/couche.tileSize.y));Ecrire(d,m);
                }
                // Le repère (x, y) → (−x, −y) retourne le sens : cet ordre fait regarder le ciel aux triangles.
                for(int i=0;i<nl;i++)for(int j=0;j<nt;j++){int a=b0+i*(nt+1)+j,b=a+nt+1;tri.AddRange(new[]{a,a+1,b,b,a+1,b+1});}
            }
            d.Append('\n');var maillage=new Mesh{name=nom,indexFormat=sommets.Count>65535?IndexFormat.UInt32:IndexFormat.UInt16};
            maillage.SetVertices(sommets);maillage.SetUVs(0,uv);maillage.SetTriangles(tri,0);maillage.RecalculateNormals();maillage.RecalculateBounds();
            go.AddComponent<MeshFilter>().sharedMesh=maillage;var rendu=go.AddComponent<MeshRenderer>();rendu.sharedMaterial=materiau;rendu.shadowCastingMode=ShadowCastingMode.Off;
        }
        static void Ecrire(StringBuilder s,Vector3 v){foreach(var c in new[]{v.x,v.y,v.z})s.Append(' ').Append(c.ToString("F2",CultureInfo.InvariantCulture));}
        static string Hacher(string texte){using var sha=SHA256.Create();return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(texte)).Select(b=>b.ToString("x2")));}
    }
}
