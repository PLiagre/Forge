using System;using System.Collections.Generic;using System.Globalization;using Forge.Pont;using UnityEngine;using Object=UnityEngine.Object;
namespace ForgeLocal3D
{
    // Lot 737 : une maison de terre par case de la base, sous « Maisons de 1400 », hors des bâtiments de geste.
    public sealed class DesertMaisons1400
    {
        const float Tol=.05f;
        public Transform Racine{get;}
        public int Posees=>Racine.childCount;
        public int Foyers{get;private set;}=-1;
        public string Absence{get;private set;}
        public readonly List<string> Refus=new();
        readonly Terrain terrain;readonly KitDesBatiments kit;
        public DesertMaisons1400(Transform parent,Terrain terrain,KitDesBatiments kit=null)
        {this.terrain=terrain;this.kit=kit?kit:KitDesBatiments.Charger();var go=new GameObject("Maisons de 1400");go.transform.SetParent(parent,false);Racine=go.transform;}
        // Vide cette seule racine. Base nulle ou pose impossible : l'absence, jamais « 0 foyer ».
        public string Dessiner(BaseDuPlan @base)
        {
            for(int i=Racine.childCount-1;i>=0;i--)Object.DestroyImmediate(Racine.GetChild(i).gameObject);
            Refus.Clear();Foyers=-1;Absence=null;
            if(@base==null){Absence="base non servie";return Ligne();}
            if(!kit){Absence="pas de kit des bâtiments";return Ligne();}
            var pose=MaisonsDeLaBase.Poser(@base);if(!pose.Presente){Absence=pose.Absence;return Ligne();}
            Foyers=pose.Cases.Count;float limite=terrain.terrainData.size.x/2f-1f;
            foreach(var c in pose.Cases)PoserUne(c,limite);return Ligne();
        }
        string Ligne(){string t=Absence!=null?"Maisons de 1400 : "+Absence:"Maisons de 1400 : "+Posees.ToString(CultureInfo.InvariantCulture)+" posée(s), "+Foyers.ToString(CultureInfo.InvariantCulture)+" foyer(s)";return Refus.Count==0?t:t+"\n"+string.Join("\n",Refus);}
        void PoserUne(CaseDeMaison c,float limite)
        {
            string nom="Maison "+c.Maison.ToString(CultureInfo.InvariantCulture)+" indice "+c.Indice.ToString(CultureInfo.InvariantCulture);var coins=Coins(c);
            foreach(var p in coins)if(Math.Abs(p.x)>limite||Math.Abs(p.y)>limite){Refus.Add(nom+" : hors du terrain");return;}
            var piece=kit.Maison((c.Maison+c.Indice)%6);if(!piece.Presente){Refus.Add(nom+" : "+piece.Absence);return;}
            if(!Boite(piece.Prefab,out var b)){Refus.Add(nom+" : mesure absente");return;}
            float echelle=Mathf.Min((float)c.LargeurM/b.size.x,(float)c.ProfondeurM/b.size.z);
            if(!(echelle>0f)||float.IsInfinity(echelle)){Refus.Add(nom+" : mesure absente");return;}
            float sol=float.PositiveInfinity;foreach(var p in coins)sol=Mathf.Min(sol,terrain.SampleHeight(new Vector3(-p.x,0,-p.y))+terrain.transform.position.y);
            var go=Object.Instantiate(piece.Prefab,Racine);go.name=nom;var rot=Quaternion.Euler(0,(float)c.LacetDegres,0);var dec=rot*(echelle*new Vector3(b.center.x,0,b.center.z));
            go.transform.SetPositionAndRotation(new Vector3(-(float)c.CentreX-dec.x,sol-echelle*b.min.y,-(float)c.CentreY-dec.z),rot);
            go.transform.localScale=new Vector3(echelle,echelle,echelle);if(Depasse(go,c)){Object.DestroyImmediate(go);Refus.Add(nom+" : déborde");}
        }
        // Vrai si un coin de boîte sort du rectangle de plus de 0,05 m. Le dessin détruit alors la pièce.
        public static bool Depasse(GameObject instance,CaseDeMaison c)
        {
            double t=c.LacetDegres*Math.PI/180,ax=-Math.Cos(t),ay=Math.Sin(t),bx=-Math.Sin(t),by=-Math.Cos(t),hw=c.LargeurM/2,hd=c.ProfondeurM/2;
            foreach(var f in instance.GetComponentsInChildren<MeshFilter>(true)){if(!f.sharedMesh)continue;var b=f.sharedMesh.bounds;for(int k=0;k<8;k++){
                var m=f.transform.TransformPoint(Sommet(b,k));double px=-m.x-c.CentreX,py=-m.z-c.CentreY,u=px*ax+py*ay,v=px*bx+py*by,ox=Math.Max(0,Math.Abs(u)-hw),oz=Math.Max(0,Math.Abs(v)-hd);
                if(ox*ox+oz*oz>Tol*(double)Tol)return true;}}
            return false;
        }
        // Boîte commune de tous les MeshFilter, tous LOD compris, dans le repère du prefab.
        public static bool Boite(GameObject prefab,out Bounds boite)
        {
            boite=new Bounds();bool vu=false;if(!prefab)return false;
            foreach(var f in prefab.GetComponentsInChildren<MeshFilter>(true)){if(!f.sharedMesh)continue;var b=f.sharedMesh.bounds;for(int k=0;k<8;k++){
                var p=prefab.transform.InverseTransformPoint(f.transform.TransformPoint(Sommet(b,k)));if(!vu){boite=new Bounds(p,Vector3.zero);vu=true;}else boite.Encapsulate(p);}}
            return vu&&boite.size.x>0f&&boite.size.z>0f&&!float.IsInfinity(boite.size.x);
        }
        public static Vector2[] Coins(CaseDeMaison c)
        {
            double t=c.LacetDegres*Math.PI/180,hw=c.LargeurM/2,hd=c.ProfondeurM/2,wx=-Math.Cos(t),wy=Math.Sin(t),dx=-Math.Sin(t),dy=-Math.Cos(t);var r=new Vector2[4];int i=0;
            for(int sx=-1;sx<=1;sx+=2)for(int sz=-1;sz<=1;sz+=2)r[i++]=new Vector2((float)(c.CentreX+sx*hw*wx+sz*hd*dx),(float)(c.CentreY+sx*hw*wy+sz*hd*dy));
            return r;
        }
        static Vector3 Sommet(Bounds b,int k)=>new Vector3((k&1)==0?b.min.x:b.max.x,(k&2)==0?b.min.y:b.max.y,(k&4)==0?b.min.z:b.max.z);
    }
}
