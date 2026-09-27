Shader "Forge/CitadelTerrain"
{
    Properties
    {
        _BaseMap("Répartition de neige du paysage",2D)="white"{}
        _RockMap("Roche : couleur",2D)="white"{}
        _RockNormal("Roche : normales",2D)="bump"{}
        _RockMask("Roche : masque HDRP",2D)="white"{}
        _SoilMap("Sol : couleur",2D)="white"{}
        _SoilNormal("Sol : normales",2D)="bump"{}
        _SoilMask("Sol : masque HDRP",2D)="white"{}
        _GravelMap("Gravier : couleur",2D)="white"{}
        _GravelNormal("Gravier : normales",2D)="bump"{}
        _GravelMask("Gravier : masque HDRP",2D)="white"{}
        _RockScale("Période roche en mètres",Float)=8
        _SoilScale("Période sol en mètres",Float)=5
        _GravelScale("Période gravier en mètres",Float)=3
        _SnowCover("Enneigement",Range(0,1))=.8
        _Valley("Sol de vallée",Float)=1
        _RockTint("Teinte roche",Color)=(.68,.73,.77,1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        TEXTURE2D(_RockMap); SAMPLER(sampler_RockMap);
        TEXTURE2D(_RockNormal); SAMPLER(sampler_RockNormal);
        TEXTURE2D(_RockMask); SAMPLER(sampler_RockMask);
        TEXTURE2D(_SoilMap); SAMPLER(sampler_SoilMap);
        TEXTURE2D(_SoilNormal); SAMPLER(sampler_SoilNormal);
        TEXTURE2D(_SoilMask); SAMPLER(sampler_SoilMask);
        TEXTURE2D(_GravelMap); SAMPLER(sampler_GravelMap);
        TEXTURE2D(_GravelNormal); SAMPLER(sampler_GravelNormal);
        TEXTURE2D(_GravelMask); SAMPLER(sampler_GravelMask);
        CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST,_RockTint;
        float _RockScale,_SoilScale,_GravelScale,_SnowCover,_Valley;
        CBUFFER_END
        float4 _AlpineAmbient;float _AlpineWet;float3 _LightDirection;
        struct A { float4 vertex:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0; };
        struct V { float4 clip:SV_POSITION;float3 world:TEXCOORD0;float3 normal:TEXCOORD1;float2 uv:TEXCOORD2;float fog:TEXCOORD3; };
        V Vert(A a)
        {
            V o;o.world=TransformObjectToWorld(a.vertex.xyz);o.clip=TransformWorldToHClip(o.world);
            o.normal=TransformObjectToWorldNormal(a.normal);o.uv=a.uv;o.fog=ComputeFogFactor(o.clip.z);return o;
        }
        V ShadowVert(A a)
        {
            V o=Vert(a);o.clip=TransformWorldToHClip(ApplyShadowBias(o.world,normalize(o.normal),_LightDirection));
            #if UNITY_REVERSED_Z
            o.clip.z=min(o.clip.z,UNITY_NEAR_CLIP_VALUE);
            #else
            o.clip.z=max(o.clip.z,UNITY_NEAR_CLIP_VALUE);
            #endif
            return o;
        }
        float Hash(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
        float Noise(float2 p)
        {
            float2 a=floor(p),f=frac(p);f=f*f*(3-2*f);
            return lerp(lerp(Hash(a),Hash(a+float2(1,0)),f.x),lerp(Hash(a+float2(0,1)),Hash(a+1),f.x),f.y);
        }
        // Projection sur trois plans : aucune texture étirée sur les falaises verticales.
        #define TRI(T,S) (SAMPLE_TEXTURE2D(T,S,ux)*w.x+SAMPLE_TEXTURE2D(T,S,uy)*w.y+SAMPLE_TEXTURE2D(T,S,uz)*w.z)
        half4 Frag(V i):SV_Target
        {
            float3 n=normalize(i.normal),w=pow(abs(n),4);w/=max(dot(w,1),.001);
            float3 p=i.world/max(_RockScale,.1),sgn=sign(n);
            float2 ux=p.zy*float2(sgn.x,1),uy=p.xz*float2(sgn.y,1),uz=p.xy*float2(-sgn.z,1);
            half3 rock=TRI(_RockMap,sampler_RockMap).rgb*_RockTint.rgb;
            half4 rm=TRI(_RockMask,sampler_RockMask);
            float3 nx=UnpackNormal(SAMPLE_TEXTURE2D(_RockNormal,sampler_RockNormal,ux));
            float3 ny=UnpackNormal(SAMPLE_TEXTURE2D(_RockNormal,sampler_RockNormal,uy));
            float3 nz=UnpackNormal(SAMPLE_TEXTURE2D(_RockNormal,sampler_RockNormal,uz));
            float3 rn=normalize(n+float3(0,nx.y,nx.x*sgn.x)*w.x*.55
                +float3(ny.x*sgn.y,0,ny.y)*w.y*.55+float3(-nz.x*sgn.z,nz.y,0)*w.z*.55);
            half3 ground=rock;float3 normal=rn;half4 mask=rm;
            // Les falaises et montagnes n'échantillonnent pas les six cartes de sol.
            [branch] if(_Valley>.5)
            {
                float2 su=i.world.xz/max(_SoilScale,.1),gu=i.world.xz/max(_GravelScale,.1);
                half3 soil=SAMPLE_TEXTURE2D(_SoilMap,sampler_SoilMap,su).rgb;
                half3 gravel=SAMPLE_TEXTURE2D(_GravelMap,sampler_GravelMap,gu).rgb;
                half4 sm=SAMPLE_TEXTURE2D(_SoilMask,sampler_SoilMask,su),gm=SAMPLE_TEXTURE2D(_GravelMask,sampler_GravelMask,gu);
                float grain=smoothstep(.35,.7,Noise(i.world.xz*.13));
                float flat=smoothstep(.58,.9,n.y);
                ground=lerp(rock,lerp(soil*.75,gravel*.8,grain),flat);
                float3 sn=UnpackNormal(SAMPLE_TEXTURE2D(_SoilNormal,sampler_SoilNormal,su));
                float3 gn=UnpackNormal(SAMPLE_TEXTURE2D(_GravelNormal,sampler_GravelNormal,gu));
                float3 small=lerp(sn,gn,grain);
                normal=normalize(lerp(rn,normalize(n+float3(small.x,0,small.y)*.48),flat));
                mask=lerp(rm,lerp(sm,gm,grain),flat);
            }
            // Variation à l'échelle de la paroi : strates sombres et grandes veines.
            float vein=Noise(i.world.xz*.032+i.world.y*.019);
            float strata=.5+.5*sin(i.world.y*.65+vein*7);
            ground*=lerp(.72,1.10,vein)*lerp(.80,1.04,smoothstep(.1,.65,strata));
            float macro=SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv).r;
            float patch=Noise(i.world.xz*.075)*.62+Noise(i.world.xz*.43)*.28+Noise(i.world.xz*2.6)*.1;
            float snow=lerp(smoothstep(.29,.78,macro)*lerp(.5,1,patch),smoothstep(1-_SnowCover+.07,1-_SnowCover+.14,patch),_Valley);
            snow*=lerp(smoothstep(.28,.82,n.y),smoothstep(.3,.82,n.y),_Valley);
            half3 snowColor=half3(.73,.81,.87)*lerp(.92,1.04,Noise(i.world.xz*1.5));
            normal=normalize(lerp(normal,n,snow*.92));
            SurfaceData surface=(SurfaceData)0;
            surface.albedo=lerp(ground*(1-_AlpineWet*.15),snowColor,snow);
            surface.metallic=0;surface.smoothness=lerp(mask.a*.32,.18,snow);
            surface.occlusion=lerp(lerp(1,mask.g,.7),1,snow);surface.alpha=1;surface.normalTS=float3(0,0,1);
            InputData data=(InputData)0;
            data.positionWS=i.world;data.normalWS=normal;data.viewDirectionWS=GetWorldSpaceNormalizeViewDir(i.world);
            data.shadowCoord=TransformWorldToShadowCoord(i.world);data.normalizedScreenSpaceUV=GetNormalizedScreenSpaceUV(i.clip);
            data.bakedGI=_AlpineAmbient.rgb*lerp(.55,1,saturate(normal.y*.5+.5));data.shadowMask=half4(1,1,1,1);
            return half4(MixFog(UniversalFragmentPBR(data,surface).rgb,i.fog),1);
        }
        half4 Depth(V i):SV_Target{return 0;}
        ENDHLSL
        Pass
        {
            Name "Forward" Tags {"LightMode"="UniversalForward"}
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_fog
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile _ _ADDITIONAL_LIGHTS
            ENDHLSL
        }
        Pass
        {
            Name "ShadowCaster" Tags {"LightMode"="ShadowCaster"}
            ZWrite On ColorMask 0
            HLSLPROGRAM
            #pragma vertex ShadowVert
            #pragma fragment Depth
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags {"LightMode"="DepthOnly"}
            ZWrite On ColorMask 0
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Depth
            ENDHLSL
        }
    }
}
