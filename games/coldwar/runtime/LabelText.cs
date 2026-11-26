using System;
using System.Xml.Linq;

// These methods are compiled into the two game display paths by the offline builder.
// The game does not load an extra plugin or execute the builder.
internal static class LabelText
{
    public static bool IsOurSource(string id, string xml)
    {
        return id == "zhcn-coldwar-local" && xml != null &&
            xml.IndexOf("<!--zhcn-coldwar-local:ui-->",0,Math.Min(xml.Length,160),StringComparison.Ordinal)>=0;
    }
    public static bool IsOurDocument(XDocument text)
    {
        if (text == null || text.Root == null)
            return false;
        XComment marker = text.Root.FirstNode as XComment;
        return marker != null && marker.Value == "zhcn-coldwar-local:ui";
    }

    public static string Local(XDocument document, string key)
    {
        XElement section = document.Root.Element("system");
        XElement line = section == null ? null : section.Element(key);
        return line == null ? null : line.Value;
    }

    public static string SteamBody(string native, XDocument document)
    {
        if (String.IsNullOrEmpty(native)) return null;
        const string init = "[Steam] SteamAPI init failed after ";
        int diagnostic = native.IndexOf(init, StringComparison.Ordinal);
        if (diagnostic >= 0 && (diagnostic == 0 || native[diagnostic-1] == '\n'))
        {
            string summary = Local(document,"error_occured");
            if (String.IsNullOrEmpty(summary)) return null;
            string raw = native.Substring(diagnostic);
            string reason = raw.IndexOf("No appID found",StringComparison.Ordinal) < 0
                ? "Steam 接口初始化失败。" : "Steam 未取得游戏的应用编号。请从 Steam 库中启动游戏。";
            return summary + "\n" + reason + "\n\nSteam 原始诊断：\n" + raw;
        }
        if (!native.StartsWith("Steam synchronization failed.",StringComparison.Ordinal)) return null;
        string cause = null;
        if (native.IndexOf("the Steam client is not running",StringComparison.OrdinalIgnoreCase) >= 0)
            cause = "steam_error_not_running";
        else if (native.IndexOf("does not provide the interface",StringComparison.OrdinalIgnoreCase) >= 0)
            cause = "steam_error_outdated_client";
        else if (native.IndexOf("no connection to it could be established",StringComparison.OrdinalIgnoreCase) >= 0)
            cause = "steam_error_no_pipe";
        string main = Local(document,"steam_error");
        if (String.IsNullOrEmpty(main)) return null;
        if (cause == null)
        {
            // Keep any unrecognized diagnostic after the standard introductory paragraph.
            int gap = native.IndexOf("\n",StringComparison.Ordinal);
            return gap < 0 ? main : main + native.Substring(gap);
        }
        string detail = Local(document,cause);
        return String.IsNullOrEmpty(detail) ? null : main + "\n\n" + detail;
    }

    public static string SteamButton(string previous, XDocument document)
    {
        if (previous == "Open log file") return Local(document,"open_log_file");
        if (previous == "OK") return Local(document,"OK");
        if (previous == "Disable mods and restart") return Local(document,"disable_mods_restart");
        return null;
    }

    public static string LanguageRow(string caption, string code, bool pending)
    {
        if (String.IsNullOrEmpty(caption) || (code != "ru" && code != "en")) return null;
        if (!pending) return caption;
        return caption + (code == "ru" ? "<size=72%> · после выхода из настроек</size>"
                                      : "<size=72%>　·　关闭设置后生效</size>");
    }

    public static string Interaction(string name)
    {
        if (name == "Press") return "按";
        if (name == "Hold") return "长按";
        if (name == "Tap") return "轻按";
        if (name == "Slow Tap") return "慢按";
        if (name == "Multi Tap") return "连按";
        return null;
    }

    public static string Bindings(string full, string controls)
    {
        if (String.IsNullOrEmpty(full) || String.IsNullOrEmpty(controls) || full == controls)
            return full;
        string[] separator = new string[] { " | " };
        string[] displayed = full.Split(separator, StringSplitOptions.None);
        string[] buttons = controls.Split(separator, StringSplitOptions.None);
        if (displayed.Length != buttons.Length)
            return full;
        for (int i = 0; i < buttons.Length; ++i)
        {
            string control = buttons[i];
            string value = displayed[i];
            if (String.IsNullOrEmpty(control) || !value.EndsWith(" " + control, StringComparison.Ordinal))
                continue;
            string hint = Interaction(value.Substring(0, value.Length - control.Length - 1));
            if (hint != null)
                displayed[i] = hint + " " + control;
        }
        return String.Join(" | ", displayed);
    }
}
