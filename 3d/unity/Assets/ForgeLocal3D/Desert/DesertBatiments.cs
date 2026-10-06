using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using Forge.Pont;
using UnityEngine;
using Object=UnityEngine.Object;

namespace ForgeLocal3D
{
    // Lot 369 : sur chaque parcelle bâtie du plan, la pièce du kit du désert qui montre l'étape du bâtiment
    // (piquets, murs ou fini). La pièce est posée au sol, au centre de l'emprise, façade tournée vers la rue,
    // sans mise à l'échelle ni inclinaison. Rien n'est décidé ici : l'étape et la pose se lisent au pont
    // (LectureDuBatiment). Une pièce absente ou qui déborde de son emprise n'est pas posée : elle se déclare.
    // Pas un composant : la scène ne change pas.
    public sealed class DesertBatiments
    {
        const float Tolerance=.05f;

        public Transform Racine{get;}
        // SHA-256 de la description du dernier dessin : une ligne par bâtiment, dans l'ordre du plan.
        public string Empreinte{get;private set;}=Hacher("");
        readonly Terrain terrain;
        readonly KitDesBatiments kit;

        public DesertBatiments(Transform parent,Terrain terrain)
        {
            kit=KitDesBatiments.Charger();
            if(!kit)throw new InvalidOperationException("Pas de kit des bâtiments (Resources/KitDesBatiments) : les bâtiments ne sont pas dessinés.");
            this.terrain=terrain;
            var go=new GameObject("Bâtiments du plan");go.transform.SetParent(parent,false);Racine=go.transform;
        }

        float Sol(Vector3 p)=>terrain.SampleHeight(p)+terrain.transform.position.y;

        public List<(long identifiant,string etat,string message)> Dessiner(IReadOnlyList<BatimentDuPlan> batiments)
        {
            // D'abord vider : un Destroy différé laisserait les anciennes pièces comptées dans la même image.
            // Maillages et matériaux sont ceux des prefabs du kit : jamais détruits.
            for(int i=Racine.childCount-1;i>=0;i--)Object.DestroyImmediate(Racine.GetChild(i).gameObject);
            var resultats=new List<(long identifiant,string etat,string message)>();var description=new StringBuilder();
            float limite=terrain.terrainData.size.x/2-1;
            foreach(var b in batiments)
            {
                string id=b.Identifiant.ToString(CultureInfo.InvariantCulture);
                if(description.Length>0)description.Append('\n');
                string cause=null,nomPiece=null;Transform piece=null;
                var pose=LectureDuBatiment.Poser(b);var etape=LectureDuBatiment.Etape(b);
                if(!pose.Presente)cause=pose.Absence;
                else if(b.Emprise.Any(c=>Math.Abs(c.X)>limite||Math.Abs(c.Y)>limite))cause="hors du terrain.";
                else
                {
                    var p=kit.Piece(b.Nature,etape);
                    if(!p.Presente)cause=p.Absence;
                    else
                    {
                        // Repère du lot 293 : (x, y) du plan devient (-x, sol, -y).
                        var centre=new Vector3((float)-pose.CentreX,0,(float)-pose.CentreY);centre.y=Sol(centre);
                        var go=Object.Instantiate(p.Prefab,Racine);go.name="Bâtiment "+id;
                        go.transform.SetPositionAndRotation(centre,Quaternion.Euler(0,(float)pose.LacetDegres,0));
                        double debord=Debord(go,b.Emprise);
                        if(debord>0)
                        {
                            Object.DestroyImmediate(go);
                            cause=p.Prefab.name+" déborde de son emprise de "+debord.ToString("F2",CultureInfo.InvariantCulture)+" m.";
                        }
                        else{piece=go.transform;nomPiece=p.Prefab.name;}
                    }
                }
                if(cause!=null)
                {
                    resultats.Add((b.Identifiant,"refusee","Bâtiment "+id+" non posé : "+cause));
                    description.Append(id).Append(" refusee");continue;
                }
                string etat=etape.ToString().ToLowerInvariant();
                description.Append(id).Append(' ').Append(etat).Append(' ').Append(nomPiece);
                var v=piece.position;
                foreach(var c in new[]{v.x,v.y,v.z,piece.eulerAngles.y})description.Append(' ').Append(c.ToString("F2",CultureInfo.InvariantCulture));
                resultats.Add((b.Identifiant,etat,""));
            }
            Empreinte=Hacher(description.ToString());
            return resultats;
        }

        // La plus grande distance, au plan, d'un coin de boîte de maillage hors de l'emprise et à plus de
        // 0,05 m de son côté le plus proche ; 0 si aucun. Tous les maillages de l'instance, tous LOD compris.
        static double Debord(GameObject instance,IReadOnlyList<PointLocal> emprise)
        {
            double pire=0;
            foreach(var filtre in instance.GetComponentsInChildren<MeshFilter>(true))
            {
                if(!filtre.sharedMesh)continue;
                var boite=filtre.sharedMesh.bounds;
                for(int k=0;k<8;k++)
                {
                    var local=new Vector3((k&1)==0?boite.min.x:boite.max.x,(k&2)==0?boite.min.y:boite.max.y,(k&4)==0?boite.min.z:boite.max.z);
                    var m=filtre.transform.TransformPoint(local);
                    double x=-m.x,y=-m.z;
                    if(Dedans(emprise,x,y))continue;
                    double d=DistanceAuBord(emprise,x,y);
                    if(d>Tolerance&&d>pire)pire=d;
                }
            }
            return pire;
        }

        // Règle pair-impair.
        static bool Dedans(IReadOnlyList<PointLocal> poly,double x,double y)
        {
            bool dedans=false;int n=poly.Count;
            for(int i=0,j=n-1;i<n;j=i++)
            {
                double xi=poly[i].X,yi=poly[i].Y,xj=poly[j].X,yj=poly[j].Y;
                if((yi>y)!=(yj>y)&&x<(xj-xi)*(y-yi)/(yj-yi)+xi)dedans=!dedans;
            }
            return dedans;
        }

        static double DistanceAuBord(IReadOnlyList<PointLocal> poly,double x,double y)
        {
            double min=double.PositiveInfinity;int n=poly.Count;
            for(int i=0;i<n;i++)
            {
                PointLocal a=poly[i],b=poly[(i+1)%n];
                double ex=b.X-a.X,ey=b.Y-a.Y,l2=ex*ex+ey*ey;
                double t=l2>0?Math.Max(0,Math.Min(1,((x-a.X)*ex+(y-a.Y)*ey)/l2)):0;
                double dx=x-(a.X+t*ex),dy=y-(a.Y+t*ey);
                min=Math.Min(min,Math.Sqrt(dx*dx+dy*dy));
            }
            return min;
        }

        static string Hacher(string texte)
        {
            using var sha=SHA256.Create();
            return string.Concat(sha.ComputeHash(Encoding.UTF8.GetBytes(texte)).Select(b=>b.ToString("x2")));
        }
    }
}
