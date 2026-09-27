Shader "Forge/CitadelLit"
{
    Properties
    {
        _BaseMap("Couleur",2D)="white"{}
        _BaseColor("Teinte",Color)=(1,1,1,1)
        _BumpMap("Normales",2D)="bump"{}
        _MetallicGlossMap("Métal et lissage",2D)="black"{}
        _HasGlossMap("Carte de surface présente",Float)=0
        _Metallic("Métal",Range(0,1))=0
        _BumpScale("Relief fin",Range(0,2))=.48
        _Weathering("Patine",Range(0,1))=0
        _Smoothness("Lissage",Range(0,1))=.2
        _Cutoff("Découpe",Range(0,1))=.35
        _AlphaClip("Découper",Float)=0
        _Wind("Vent",Float)=0
        _WindHeight("Hauteur de flexion",Float)=12
        _MaskMap("Masque HDRP : métal, occlusion, détail, lissage",2D)="white"{}
        _HasMaskMap("Masque HDRP présent",Float)=0
        _Banner("Tissu suspendu",Float)=0
        _SnowFactor("Neige",Float)=.4
        _SnowBase("Neige permanente",Float)=0
        _EmissionColor("Fenêtres",Color)=(0,0,0,0)
        _Cull("Faces",Float)=0
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Cull Off
        AlphaToMask On
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
        TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
        TEXTURE2D(_BumpMap); SAMPLER(sampler_BumpMap);
        TEXTURE2D(_MetallicGlossMap); SAMPLER(sampler_MetallicGlossMap);
        TEXTURE2D(_MaskMap); SAMPLER(sampler_MaskMap);
        CBUFFER_START(UnityPerMaterial)
        float4 _BaseMap_ST,_BaseColor,_EmissionColor;
        float _Cutoff,_AlphaClip,_Wind,_SnowFactor,_Smoothness,_Banner,_HasGlossMap,_Metallic,_BumpScale,_Weathering;
        float _WindHeight,_HasMaskMap,_SnowBase;
        CBUFFER_END
        float _AlpineWind,_AlpineSnow,_AlpineWet,_AlpineNight,_AlpineDaylight;
        float4 _AlpineAmbient;
        float3 _LightDirection;
        struct A { float4 vertex:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;UNITY_VERTEX_INPUT_INSTANCE_ID };
        struct V { float4 clip:SV_POSITION;float3 world:TEXCOORD0;float3 normal:TEXCOORD1;float2 uv:TEXCOORD2;float fog:TEXCOORD3;UNITY_VERTEX_INPUT_INSTANCE_ID };
        float3 Bend(float3 p)
        {
            float3 origin=TransformObjectToWorld(float3(0,0,0));
            float phase=origin.x*.075+origin.z*.08;
            float weight=pow(saturate(p.y/max(_WindHeight,.1)),1.7);
            p.x+=sin(_Time.y*1.15+phase+p.y*.12)*weight*_Wind*_AlpineWind*.42;
            p.z+=cos(_Time.y*.82+phase)*weight*_Wind*_AlpineWind*.24;
            float cloth=saturate((7-p.y)/3.8)*saturate(abs(p.x))*step(3.15,p.y)*step(p.y,7.05);
            p.z+=sin(_Time.y*2.5+p.x*2.7+p.y*1.8+phase)*cloth*_Banner*_AlpineWind*.34;
            return p;
        }
        V Vert(A a)
        {
            V o;UNITY_SETUP_INSTANCE_ID(a);UNITY_TRANSFER_INSTANCE_ID(a,o);
            o.world=TransformObjectToWorld(Bend(a.vertex.xyz));o.clip=TransformWorldToHClip(o.world);
            o.normal=TransformObjectToWorldNormal(a.normal);o.uv=TRANSFORM_TEX(a.uv,_BaseMap);o.fog=ComputeFogFactor(o.clip.z);return o;
        }
        V ShadowVert(A a)
        {
            V o=Vert(a);
            o.clip=TransformWorldToHClip(ApplyShadowBias(o.world,normalize(o.normal),_LightDirection));
            #if UNITY_REVERSED_Z
            o.clip.z=min(o.clip.z,UNITY_NEAR_CLIP_VALUE);
            #else
            o.clip.z=max(o.clip.z,UNITY_NEAR_CLIP_VALUE);
            #endif
            return o;
        }
        half4 Frag(V i,bool front:SV_IsFrontFace):SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(i);
            half4 tex=SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv)*_BaseColor;
            if(_AlphaClip>.5)clip(tex.a-_Cutoff);
            float3 normal=normalize(i.normal)*(front?1:-1);
            float3 dp1=ddx(i.world),dp2=ddy(i.world);float2 duv1=ddx(i.uv),duv2=ddy(i.uv);
            float3 tangent=cross(dp2,normal)*duv1.x+cross(normal,dp1)*duv2.x;
            float3 bitangent=cross(dp2,normal)*duv1.y+cross(normal,dp1)*duv2.y;
            float inv=rsqrt(max(max(dot(tangent,tangent),dot(bitangent,bitangent)),1e-10));
            float3 map=UnpackNormal(SAMPLE_TEXTURE2D(_BumpMap,sampler_BumpMap,i.uv));
            map.xy*=_BumpScale;
            normal=normalize(tangent*inv*map.x+bitangent*inv*map.y+normal*map.z);
            float snow=saturate((_AlpineSnow+_SnowBase)*_SnowFactor*pow(saturate(normal.y),2)*1.7);
            float3 color=lerp(tex.rgb*(1-_AlpineWet*.22),float3(.82,.88,.92),snow);
            // Variation lente des surfaces ; les joints fins viennent des cartes normales.
            float patina=.5+.25*sin(i.world.x*.41+i.world.z*.32)+.25*sin(i.world.y*.75-i.world.x*.17);
            color*=1-patina*_Weathering;
            half4 packed=SAMPLE_TEXTURE2D(_MetallicGlossMap,sampler_MetallicGlossMap,i.uv);
            SurfaceData surface=(SurfaceData)0;
            surface.albedo=color;
            surface.metallic=lerp(_Metallic,packed.r,_HasGlossMap);
            surface.smoothness=lerp(_Smoothness,packed.a*_Smoothness,_HasGlossMap);
            surface.normalTS=map;surface.occlusion=1;surface.alpha=1;
            if(_HasMaskMap>.5)
            {
                half4 mask=SAMPLE_TEXTURE2D(_MaskMap,sampler_MaskMap,i.uv);
                surface.metallic=mask.r*_Metallic;
                surface.occlusion=lerp(1,mask.g,.7);
                surface.smoothness=mask.a*_Smoothness;
            }
            // Le plomb des vitraux reste sombre : l'émission suit la couleur de chaque verre.
            surface.emission=tex.rgb*_EmissionColor.rgb*_AlpineNight;
            InputData data=(InputData)0;
            data.positionWS=i.world;data.normalWS=normal;
            data.viewDirectionWS=GetWorldSpaceNormalizeViewDir(i.world);
            data.shadowCoord=TransformWorldToShadowCoord(i.world);
            data.normalizedScreenSpaceUV=GetNormalizedScreenSpaceUV(i.clip);
            data.bakedGI=_AlpineAmbient.rgb*lerp(.55,1,saturate(normal.y*.5+.5));
            data.shadowMask=half4(1,1,1,1);
            float3 lit=UniversalFragmentPBR(data,surface).rgb;
            return half4(MixFog(lit,i.fog),_AlphaClip>.5?tex.a:1);
        }
        half4 Shadow(V i):SV_Target
        {
            UNITY_SETUP_INSTANCE_ID(i);
            if(_AlphaClip>.5)clip(SAMPLE_TEXTURE2D(_BaseMap,sampler_BaseMap,i.uv).a-_Cutoff);
            return 0;
        }
        ENDHLSL
        Pass
        {
            Name "Forward" Tags {"LightMode"="UniversalForward"}
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Frag
            #pragma multi_compile_instancing
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
            #pragma fragment Shadow
            #pragma multi_compile_instancing
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags {"LightMode"="DepthOnly"}
            ZWrite On ColorMask 0
            HLSLPROGRAM
            #pragma vertex Vert
            #pragma fragment Shadow
            #pragma multi_compile_instancing
            ENDHLSL
        }
    }
}
