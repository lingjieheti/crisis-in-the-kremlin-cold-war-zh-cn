using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mono.Cecil;
using Mono.Cecil.Cil;

// Offline builder. All rewritten call sites belong to the game's two label renderers.
internal static class BuildLabels
{
    static void Require(bool ok, string message)
    {
        if (!ok) throw new InvalidOperationException(message);
    }

    static MethodDefinition Define(TypeDefinition owner, string name, TypeReference result, bool isStatic)
    {
        var attrs = MethodAttributes.Assembly | MethodAttributes.HideBySig;
        if (isStatic) attrs |= MethodAttributes.Static;
        var method = new MethodDefinition(name, attrs, result);
        owner.Methods.Add(method);
        return method;
    }

    // Copy the three authored, dependency-free text functions. No original method is copied
    // from another depot. BCL references use the original game's target framework.
    static Dictionary<string, MethodDefinition> AddTextFunctions(ModuleDefinition module, string templatePath, bool binding)
    {
        using (var donor = AssemblyDefinition.ReadAssembly(templatePath))
        {
            var sourceType = donor.MainModule.GetType("LabelText");
            var owner = new TypeDefinition("Frontend.Settings", "ChineseLabelText",
                TypeAttributes.NotPublic | TypeAttributes.Abstract | TypeAttributes.Sealed, module.TypeSystem.Object);
            module.Types.Add(owner);
            var functions = new Dictionary<string, MethodDefinition>();
            var authored = sourceType.Methods.Where(m => binding || (m.Name != "Interaction" && m.Name != "Bindings")).ToList();
            foreach (var method in authored)
            {
                var target = Define(owner, method.Name, module.ImportReference(method.ReturnType), true);
                foreach (var arg in method.Parameters)
                    target.Parameters.Add(new ParameterDefinition(arg.Name, arg.Attributes, module.ImportReference(arg.ParameterType)));
                functions.Add(method.Name, target);
            }
            foreach (var method in authored)
            {
                var target = functions[method.Name];
                target.Body.InitLocals = method.Body.InitLocals;
                foreach (var local in method.Body.Variables)
                    target.Body.Variables.Add(new VariableDefinition(module.ImportReference(local.VariableType)));
                var mapping = method.Body.Instructions.ToDictionary(i => i, i => Instruction.Create(OpCodes.Nop));
                foreach (var original in method.Body.Instructions)
                {
                    var copy = mapping[original];
                    copy.OpCode = original.OpCode;
                    object v = original.Operand;
                    if (v is Instruction) v = mapping[(Instruction)v];
                    else if (v is Instruction[]) v = ((Instruction[])v).Select(i => mapping[i]).ToArray();
                    else if (v is VariableDefinition) v = target.Body.Variables[((VariableDefinition)v).Index];
                    else if (v is ParameterDefinition) v = target.Parameters[((ParameterDefinition)v).Index];
                    else if (v is MethodReference)
                    {
                        var reference = (MethodReference)v;
                        v = reference.DeclaringType.FullName == sourceType.FullName
                            ? functions[reference.Name] : module.ImportReference(reference);
                    }
                    else if (v is TypeReference) v = module.ImportReference((TypeReference)v);
                    copy.Operand = v;
                    target.Body.Instructions.Add(copy);
                }
                Require(!method.Body.HasExceptionHandlers, "Unexpected exception regions in authored text functions");
            }
            return functions;
        }
    }

    static FieldDefinition Field(TypeDefinition type, string name)
    {
        return type.Fields.Single(f => f.Name == name);
    }

    static bool Call(Instruction i, string type, string name)
    {
        var reference = i.Operand as MethodReference;
        return reference != null && reference.DeclaringType.FullName == type && reference.Name == name;
    }

    static MethodDefinition Active(ModuleDefinition module, TypeDefinition manager, MethodDefinition textCheck, MethodDefinition selected)
    {
        var document = Field(manager,"gameText");
        var active = Define(manager, "LocalChineseDisplayDocument", document.FieldType, true);
        var il = active.Body.GetILProcessor();
        var no = Instruction.Create(OpCodes.Ldnull);
        var instance = Field(manager, "inst");
        il.Emit(OpCodes.Call,selected);
        il.Emit(OpCodes.Brfalse,no);
        il.Emit(OpCodes.Ldsfld, instance);
        il.Emit(OpCodes.Brfalse, no);
        il.Emit(OpCodes.Ldsfld, instance);
        il.Emit(OpCodes.Ldfld, Field(manager,"language"));
        il.Emit(OpCodes.Ldc_I4_S, (sbyte)10); // UnityEngine.SystemLanguage.English
        il.Emit(OpCodes.Bne_Un, no);
        il.Emit(OpCodes.Ldsfld, instance);
        il.Emit(OpCodes.Ldfld, document);
        il.Emit(OpCodes.Call, textCheck);
        il.Emit(OpCodes.Brfalse, no);
        il.Emit(OpCodes.Ldsfld, instance);
        il.Emit(OpCodes.Ldfld, document);
        il.Emit(OpCodes.Ret);
        il.Append(no);
        il.Emit(OpCodes.Ret);
        return active;
    }

    // A Steam startup failure may queue its message before the Workshop translation
    // has been parsed. Repaint just the already visible text components after either
    // the language document or the visible message changes. Keep the original queue,
    // message objects, diagnostic log, timers, buttons and callbacks intact.
    static void SteamNotice(ModuleDefinition module, TypeDefinition language, MethodDefinition active,
                            Dictionary<string, MethodDefinition> labels)
    {
        var manager = module.GetType("Backend.Managers.MessageManager");
        var display = manager.Methods.Single(m => m.Name == "DisplayMessage");
        var parse = language.Methods.Single(m => m.Name == "ParseGameTextFromXMLString");
        var messageField = Field(manager,"currentlyDisplayed");
        var messageBody = Field(messageField.FieldType.Resolve(),"messageText");
        var setText = (MethodReference)display.Body.Instructions.First(i=>Call(i,"TMPro.TMP_Text","SetText")).Operand;
        var getText = new MethodReference("get_text",module.TypeSystem.String,setText.DeclaringType) { HasThis=true };
        var redraw = Define(manager,"RefreshChineseSteamText",module.TypeSystem.Void,true);
        var doc = new VariableDefinition(active.ReturnType);
        var owner = new VariableDefinition(manager);
        var text = new VariableDefinition(module.TypeSystem.String);
        var button = new VariableDefinition(setText.DeclaringType);
        var index = new VariableDefinition(module.TypeSystem.Int32);
        var controls=Field(manager,"buttonsTexts");
        var cached=new FieldDefinition("chineseNoticeOwner",FieldAttributes.Private | FieldAttributes.NotSerialized,messageField.FieldType);
        var originals=new FieldDefinition("chineseNoticeButtons",FieldAttributes.Private | FieldAttributes.NotSerialized,new ArrayType(module.TypeSystem.String));
        manager.Fields.Add(cached); manager.Fields.Add(originals);
        var il = redraw.Body.GetILProcessor();
        redraw.Body.InitLocals=true;
        foreach(var v in new []{doc,owner,text,button,index}) redraw.Body.Variables.Add(v);
        var finish=Instruction.Create(OpCodes.Ret);
        il.Emit(OpCodes.Call,active); il.Emit(OpCodes.Stloc,doc);
        il.Emit(OpCodes.Ldsfld,Field(manager,"inst")); il.Emit(OpCodes.Stloc,owner);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Brfalse,finish);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,messageField); il.Emit(OpCodes.Brfalse,finish);
        // A later Workshop translation can become the winning document after the
        // first startup message is already visible. Restore this exact message's
        // original labels without replaying its buttons, timer or queue.
        var translate=Instruction.Create(OpCodes.Ldloc,owner);
        il.Emit(OpCodes.Ldloc,doc); il.Emit(OpCodes.Brtrue,translate);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,cached);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,messageField); il.Emit(OpCodes.Bne_Un,finish);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,Field(manager,"mainText"));
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,messageField); il.Emit(OpCodes.Ldfld,messageBody);
        il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Callvirt,setText);
        var restoreLoop=Instruction.Create(OpCodes.Ldloc,index);
        var nextButton=Instruction.Create(OpCodes.Ldloc,index);
        var clear=Instruction.Create(OpCodes.Ldloc,owner);
        il.Append(restoreLoop);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,originals); il.Emit(OpCodes.Ldlen); il.Emit(OpCodes.Conv_I4);
        il.Emit(OpCodes.Bge,clear);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,originals); il.Emit(OpCodes.Ldloc,index);
        il.Emit(OpCodes.Ldelem_Ref); il.Emit(OpCodes.Stloc,text); il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Brfalse,nextButton);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,controls); il.Emit(OpCodes.Ldloc,index); il.Emit(OpCodes.Ldelem_Ref);
        il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Callvirt,setText);
        il.Append(nextButton); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Add); il.Emit(OpCodes.Stloc,index);
        il.Emit(OpCodes.Br,restoreLoop);
        il.Append(clear); il.Emit(OpCodes.Ldnull); il.Emit(OpCodes.Stfld,cached);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldnull); il.Emit(OpCodes.Stfld,originals);
        il.Emit(OpCodes.Ret);
        il.Append(translate); il.Emit(OpCodes.Ldfld,messageField); il.Emit(OpCodes.Ldfld,messageBody);
        il.Emit(OpCodes.Ldloc,doc); il.Emit(OpCodes.Call,labels["SteamBody"]); il.Emit(OpCodes.Stloc,text);
        il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Brfalse,finish);
        var paint=Instruction.Create(OpCodes.Ldloc,owner);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,cached);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,messageField); il.Emit(OpCodes.Beq,paint);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,messageField); il.Emit(OpCodes.Stfld,cached);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,controls); il.Emit(OpCodes.Ldlen);
        il.Emit(OpCodes.Conv_I4); il.Emit(OpCodes.Newarr,module.TypeSystem.String); il.Emit(OpCodes.Stfld,originals);
        il.Append(paint); il.Emit(OpCodes.Ldfld,Field(manager,"mainText"));
        il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Callvirt,setText);
        var next=Instruction.Create(OpCodes.Ldloc,index);
        var loop=Instruction.Create(OpCodes.Ldloc,index);
        il.Append(loop);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,controls); il.Emit(OpCodes.Ldlen);
        il.Emit(OpCodes.Conv_I4); il.Emit(OpCodes.Bge,finish);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,controls); il.Emit(OpCodes.Ldloc,index);
        il.Emit(OpCodes.Ldelem_Ref); il.Emit(OpCodes.Stloc,button);
        il.Emit(OpCodes.Ldloc,button); il.Emit(OpCodes.Brfalse,next);
        il.Emit(OpCodes.Ldloc,button); il.Emit(OpCodes.Callvirt,getText); il.Emit(OpCodes.Ldloc,doc);
        il.Emit(OpCodes.Call,labels["SteamButton"]); il.Emit(OpCodes.Stloc,text);
        il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Brfalse,next);
        il.Emit(OpCodes.Ldloc,owner); il.Emit(OpCodes.Ldfld,originals); il.Emit(OpCodes.Ldloc,index);
        il.Emit(OpCodes.Ldloc,button); il.Emit(OpCodes.Callvirt,getText); il.Emit(OpCodes.Stelem_Ref);
        il.Emit(OpCodes.Ldloc,button); il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Ldc_I4_1);
        il.Emit(OpCodes.Callvirt,setText);
        il.Append(next); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Add); il.Emit(OpCodes.Stloc,index);
        il.Emit(OpCodes.Br,loop); il.Append(finish);
        foreach(var method in new []{display,parse})
        {
            var code=method.Body.GetILProcessor();
            // Retain existing branch targets: replace the return instruction in place.
            foreach(var tail in method.Body.Instructions.Where(i=>i.OpCode==OpCodes.Ret).ToList())
            {
                tail.OpCode=OpCodes.Call; tail.Operand=redraw;
                code.InsertAfter(tail,Instruction.Create(OpCodes.Ret));
            }
        }
    }

    static MethodDefinition EnglishTarget(ModuleDefinition module, TypeDefinition language, MethodDefinition sourceCheck)
    {
        var mods=module.GetType("Backend.Managers.ModsManager");
        var load=mods.Methods.Single(m=>m.Name=="LoadTranslationMod");
        var entry=load.Parameters[0].ParameterType.Resolve();
        var info=Field(entry,"modInfo");
        var xml=Field(mods,"translationText");
        var winner=new FieldDefinition("localChineseTranslation",FieldAttributes.Private | FieldAttributes.NotSerialized,module.TypeSystem.Boolean);
        mods.Fields.Add(winner);
        var store=load.Body.Instructions.Single(i=>i.OpCode==OpCodes.Stfld && i.Operand==xml);
        var next=store.Next;
        var writer=load.Body.GetILProcessor();
        writer.InsertBefore(next,Instruction.Create(OpCodes.Ldarg_0));
        writer.InsertBefore(next,Instruction.Create(OpCodes.Ldarg_1));
        writer.InsertBefore(next,Instruction.Create(OpCodes.Ldfld,info));
        writer.InsertBefore(next,Instruction.Create(OpCodes.Ldfld,Field(info.FieldType.Resolve(),"id")));
        writer.InsertBefore(next,Instruction.Create(OpCodes.Ldarg_0));
        writer.InsertBefore(next,Instruction.Create(OpCodes.Ldfld,xml));
        writer.InsertBefore(next,Instruction.Create(OpCodes.Call,sourceCheck));
        writer.InsertBefore(next,Instruction.Create(OpCodes.Stfld,winner));
        var selected=Define(mods,"LoadedChineseTarget",module.TypeSystem.String,true);
        var get=selected.Body.GetILProcessor();
        var empty=Instruction.Create(OpCodes.Ldnull);
        get.Emit(OpCodes.Ldsfld,Field(mods,"inst")); get.Emit(OpCodes.Brfalse,empty);
        get.Emit(OpCodes.Ldsfld,Field(mods,"inst")); get.Emit(OpCodes.Ldfld,winner); get.Emit(OpCodes.Brfalse,empty);
        get.Emit(OpCodes.Ldsfld,Field(mods,"inst")); get.Emit(OpCodes.Ldfld,xml); get.Emit(OpCodes.Ret);
        get.Append(empty); get.Emit(OpCodes.Ret);

        // The built-in translation loader otherwise replaces even a Russian document.
        // Skip just the winning, marked local pack while a different language is active.
        var parse=language.Methods.Single(m=>m.Name=="ParseGameTextFromXMLString");
        var old=parse.Body.Instructions[0];
        var filter=parse.Body.GetILProcessor();
        filter.InsertBefore(old,Instruction.Create(OpCodes.Ldarg_0));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Ldfld,Field(language,"language")));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Ldc_I4_S,(sbyte)10));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Beq,old));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Ldarg_1));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Brfalse,old));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Ldarg_1));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Call,selected));
        filter.InsertBefore(old,Instruction.Create(OpCodes.Bne_Un,old)); // Same instance cached by ModsManager.
        filter.InsertBefore(old,Instruction.Create(OpCodes.Ret));

        // A language change reloads stock text, then remerges data mods. Select the
        // winning local Chinese text at that same base-document step on English only.
        var choose=Define(language,"LocalizeEnglishSource",module.TypeSystem.String,false);
        choose.Parameters.Add(new ParameterDefinition(module.TypeSystem.String));
        var select=choose.Body.GetILProcessor();
        var stock=Instruction.Create(OpCodes.Ldarg_1);
        var have=Instruction.Create(OpCodes.Ret);
        select.Emit(OpCodes.Ldarg_0); select.Emit(OpCodes.Ldfld,Field(language,"language"));
        select.Emit(OpCodes.Ldc_I4_S,(sbyte)10); select.Emit(OpCodes.Bne_Un,stock);
        select.Emit(OpCodes.Call,selected); select.Emit(OpCodes.Dup); select.Emit(OpCodes.Brtrue,have);
        select.Emit(OpCodes.Pop); select.Append(stock); select.Append(have);
        foreach(var method in language.Methods.Where(m=>m.Name=="ApplyNewLanguage" || m.Name=="ReloadCurrentLanguageText"))
        {
            var call=method.Body.Instructions.Single(i=>i.Operand==parse);
            var il=method.Body.GetILProcessor();
            var text=new VariableDefinition(module.TypeSystem.String);
            method.Body.Variables.Add(text);
            il.InsertBefore(call,Instruction.Create(OpCodes.Stloc,text));
            il.InsertBefore(call,Instruction.Create(OpCodes.Dup));
            il.InsertBefore(call,Instruction.Create(OpCodes.Ldloc,text));
            il.InsertBefore(call,Instruction.Create(OpCodes.Call,choose));
        }
        return selected;
    }

    static void Slot(ModuleDefinition module, TypeDefinition manager, MethodDefinition selected)
    {
        var settings = module.GetType("Frontend.Settings.SettingsLanguageHandler");
        var method = settings.Methods.Single(m => m.Name == "Repaint");
        var write = method.Body.Instructions.Single(i => Call(i, "TMPro.TMP_Text","SetText"));
        var name = write.Previous.Previous;
        Require(name.OpCode == OpCodes.Ldloc_1, "Unsupported language name display");
        var il = method.Body.GetILProcessor();
        il.InsertBefore(name, Instruction.Create(OpCodes.Call, selected));
        il.InsertBefore(name, Instruction.Create(OpCodes.Brfalse, name));
        il.InsertBefore(name, Instruction.Create(OpCodes.Ldsfld, Field(manager, "inst")));
        il.InsertBefore(name, Instruction.Create(OpCodes.Ldfld, Field(manager, "tempLanguage")));
        il.InsertBefore(name, Instruction.Create(OpCodes.Ldc_I4_S, (sbyte)10));
        il.InsertBefore(name, Instruction.Create(OpCodes.Bne_Un, name));
        il.InsertBefore(name, Instruction.Create(OpCodes.Ldstr, "简体中文"));
        il.InsertBefore(name, Instruction.Create(OpCodes.Stloc_1));
    }

    // Recent depots put their one-time language tip behind the settings canvas.
    // Present that same information in the visible language row whenever our
    // translation is selected. Other translations retain their native notification.
    static void InlineSettingHint(ModuleDefinition module, TypeDefinition language, MethodDefinition selected, MethodDefinition format)
    {
        var settings=module.GetType("Frontend.Settings.SettingsLanguageHandler");
        var change=settings.Methods.Single(m=>m.Name=="ChangeLanguage");
        if(!change.Body.Instructions.Any(i=>i.OpCode==OpCodes.Ldstr && (string)i.Operand=="language_will_change_on_exit")) return;
        var showed=change.Body.Instructions.Single(i=>i.OpCode==OpCodes.Stfld && i.Operand==Field(settings,"toldThisVisit"));
        Require(change.Body.Instructions.Count(i=>Call(i,"Backend.Managers.MessageManager","AddMessage"))==1,"Unexpected language tip");
        var repaint=settings.Methods.Single(m=>m.Name=="Repaint");
        var setText=(MethodReference)repaint.Body.Instructions.Single(i=>Call(i,"TMPro.TMP_Text","SetText")).Operand;
        var refs=module.GetMemberReferences().OfType<MethodReference>().ToList();
        var transform=refs.First(r=>r.DeclaringType.FullName=="UnityEngine.Component" && r.Name=="get_transform");
        var find=refs.First(r=>r.DeclaringType.FullName=="UnityEngine.Transform" && r.Name=="Find" && r.Parameters.Count==1);
        var getComponent=new MethodReference("GetComponent",transform.DeclaringType,transform.DeclaringType){HasThis=true};
        getComponent.Parameters.Add(new ParameterDefinition(module.ImportReference(typeof(Type))));
        var localize=language.Methods.Single(m=>m.Name=="get_Item" && m.Parameters.Count==2);
        var inst=Field(language,"inst");
        var paint=Define(settings,"PaintChineseLanguageHint",module.TypeSystem.Boolean,false);
        paint.Body.InitLocals=true;
        var row=new VariableDefinition(transform.ReturnType);
        var label=new VariableDefinition(setText.DeclaringType);
        var text=new VariableDefinition(module.TypeSystem.String);
        foreach(var v in new[]{row,label,text})paint.Body.Variables.Add(v);
        var il=paint.Body.GetILProcessor();
        var no=Instruction.Create(OpCodes.Ldc_I4_0);
        il.Emit(OpCodes.Call,selected); il.Emit(OpCodes.Brfalse,no);
        il.Emit(OpCodes.Ldarg_0); il.Emit(OpCodes.Call,transform);
        il.Emit(OpCodes.Ldstr,"Scroll View/Viewport/Content/Text (0)"); il.Emit(OpCodes.Callvirt,find);
        il.Emit(OpCodes.Stloc,row); il.Emit(OpCodes.Ldloc,row); il.Emit(OpCodes.Brfalse,no);
        il.Emit(OpCodes.Ldloc,row); il.Emit(OpCodes.Ldtoken,Field(settings,"textField").FieldType);
        il.Emit(OpCodes.Call,module.ImportReference(typeof(Type).GetMethod("GetTypeFromHandle")));
        il.Emit(OpCodes.Callvirt,getComponent); il.Emit(OpCodes.Isinst,setText.DeclaringType);
        il.Emit(OpCodes.Stloc,label); il.Emit(OpCodes.Ldloc,label); il.Emit(OpCodes.Brfalse,no);
        il.Emit(OpCodes.Ldsfld,inst); il.Emit(OpCodes.Ldstr,"settings"); il.Emit(OpCodes.Ldstr,"language"); il.Emit(OpCodes.Callvirt,localize);
        il.Emit(OpCodes.Ldsfld,inst); il.Emit(OpCodes.Callvirt,language.Methods.Single(m=>m.Name=="get_CurrentCode"));
        il.Emit(OpCodes.Ldsfld,inst); il.Emit(OpCodes.Ldfld,Field(language,"language"));
        il.Emit(OpCodes.Ldsfld,inst); il.Emit(OpCodes.Ldfld,Field(language,"tempLanguage"));
        il.Emit(OpCodes.Ceq); il.Emit(OpCodes.Ldc_I4_0); il.Emit(OpCodes.Ceq);
        il.Emit(OpCodes.Call,format); il.Emit(OpCodes.Stloc,text); il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Brfalse,no);
        il.Emit(OpCodes.Ldloc,label); il.Emit(OpCodes.Ldloc,text); il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Callvirt,setText);
        il.Emit(OpCodes.Ldc_I4_1); il.Emit(OpCodes.Ret); il.Append(no); il.Emit(OpCodes.Ret);
        var end=repaint.Body.Instructions.Last();
        Require(end.OpCode==OpCodes.Ret,"Unexpected language renderer exit");
        var code=repaint.Body.GetILProcessor();
        code.InsertBefore(end,Instruction.Create(OpCodes.Ldarg_0));
        code.InsertBefore(end,Instruction.Create(OpCodes.Call,paint));
        code.InsertBefore(end,Instruction.Create(OpCodes.Pop));
        var original=showed.Next;
        code=change.Body.GetILProcessor();
        code.InsertBefore(original,Instruction.Create(OpCodes.Ldarg_0));
        code.InsertBefore(original,Instruction.Create(OpCodes.Call,paint));
        code.InsertBefore(original,Instruction.Create(OpCodes.Brfalse,original));
        code.InsertBefore(original,Instruction.Create(OpCodes.Ret));
    }

    static void Orrery(ModuleDefinition module, TypeDefinition orrery, MethodDefinition active, MethodDefinition labels)
    {
        var start = orrery.Methods.Single(m => m.Name == "Start");
        var body = start.Body;
        var findAction = body.Instructions.Single(i => Call(i, "UnityEngine.InputSystem.InputActionAsset", "FindAction"));
        var display = body.Instructions.Single(i => Call(i, "UnityEngine.InputSystem.InputActionRebindingExtensions", "GetBindingDisplayString"));
        var save = display.Next;
        Require(save.OpCode == OpCodes.Stfld && ((FieldReference)save.Operand).Name == "key", "Unsupported original shortcut capture");
        var original = (FieldDefinition)save.Operand;
        var closure = original.DeclaringType;
        var action = new FieldDefinition("chineseBindingAction", FieldAttributes.Assembly, ((MethodReference)findAction.Operand).ReturnType);
        closure.Fields.Add(action);
        var actionLocal = new VariableDefinition(action.FieldType);
        body.Variables.Add(actionLocal);
        var il = body.GetILProcessor();
        var keep = Instruction.Create(OpCodes.Dup);
        il.InsertAfter(findAction, keep);
        il.InsertAfter(keep, Instruction.Create(OpCodes.Stloc, actionLocal));
        var next = save.Next;
        il.InsertBefore(next, Instruction.Create(OpCodes.Ldloc_0));
        il.InsertBefore(next, Instruction.Create(OpCodes.Ldloc, actionLocal));
        il.InsertBefore(next, Instruction.Create(OpCodes.Stfld, action));
        var resolve = Define(closure, "ChineseShortcutLabel", module.TypeSystem.String, false);
        var render = resolve.Body.GetILProcessor();
        var fallback = Instruction.Create(OpCodes.Ldarg_0);
        render.Emit(OpCodes.Call, active);
        render.Emit(OpCodes.Brfalse, fallback);
        render.Emit(OpCodes.Ldarg_0);
        render.Emit(OpCodes.Ldfld, action);
        render.Emit(OpCodes.Brfalse, fallback);
        // Query the current binding twice. Option 4 suppresses only the interaction
        // description, retaining the same controls, device mask and player overrides.
        foreach (int flags in new int[] {0,4})
        {
            render.Emit(OpCodes.Ldarg_0);
            render.Emit(OpCodes.Ldfld, action);
            render.Emit(OpCodes.Ldc_I4, flags);
            render.Emit(OpCodes.Ldnull);
            render.Emit(OpCodes.Call, (MethodReference)display.Operand);
        }
        render.Emit(OpCodes.Call, labels);
        render.Emit(OpCodes.Ret);
        render.Append(fallback);
        render.Emit(OpCodes.Ldfld, original);
        render.Emit(OpCodes.Ret);
        var reads = new[] {start}.Concat(closure.Methods.Where(m => m != resolve && m.HasBody))
            .SelectMany(m => m.Body.Instructions)
            .Where(i => i.OpCode == OpCodes.Ldfld && i.Operand == original).ToList();
        Require(reads.Count == 2, "Unsupported initial and live shortcut presenters");
        foreach (var read in reads) { read.OpCode = OpCodes.Call; read.Operand = resolve; }
    }

    static int Main(string[] args)
    {
        using (var resolver = new DefaultAssemblyResolver())
        {
            resolver.AddSearchDirectory(Path.GetDirectoryName(Path.GetFullPath(args[0])));
            using (var assembly = AssemblyDefinition.ReadAssembly(args[0], new ReaderParameters { AssemblyResolver = resolver }))
            {
            var module = assembly.MainModule;
            bool binding = args[3] == "26955082";
            var labels = AddTextFunctions(module, args[2], binding);
            var manager = module.GetType("Backend.Managers.LanguageManager");
            var selected = EnglishTarget(module,manager,labels["IsOurSource"]);
            var active = Active(module, manager, labels["IsOurDocument"],selected);
            Slot(module, manager, selected);
            InlineSettingHint(module, manager, selected, labels["LanguageRow"]);
            SteamNotice(module, manager, active, labels);
            var orrery = module.GetType("Frontend.Orrery.OrreryController");
            if (binding) Orrery(module, orrery, active, labels["Bindings"]);
            assembly.Write(args[1]);
            }
        }
        return 0;
    }
}
