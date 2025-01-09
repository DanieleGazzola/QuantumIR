#include "slang/ast/Compilation.h"
#include "slang/driver/Driver.h"
#include "slang/util/VersionInfo.h"
#include "slang/ast/ASTSerializer.h"
#include "slang/text/Json.h"
#include "slang/ast/symbols/CompilationUnitSymbols.h"

#include <iostream>
#include <fstream>
#include <string>

using namespace slang;
using namespace slang::driver;
using namespace slang::ast;

/*
    Main program. It uses the Slang library to compute the AST of the input SystemVerilog file.
*/
int main(int argc, char **argv)
{

    if (argc < 2)
    {
        std::cerr << "Usage: " << argv[0] << " <filename>" << std::endl;
        return 1;
    }

    // Convert the filename from argv[1] to a std::string
    std::string fullPath = argv[1];

    // Find the position of the last slash
    size_t lastSlashPos = fullPath.find_last_of("/\\");
    std::string filename;

    if (lastSlashPos != std::string::npos)
    {
        // Extract the filename following the last slash
        filename = fullPath.substr(lastSlashPos + 1);
    }
    else
    {
        // If no slash is found, the entire string is the filename
        filename = fullPath;
    }
    std::cout << "Chosen Verilog input file: " << filename << "\n"
              << std::endl;
    std::ofstream file("output.json", std::ios::trunc);

    Driver driver;
    driver.addStandardArgs();

    if (!driver.parseCommandLine(argc, argv))
        return 1;

    if (!driver.processOptions())
        return 2;

    bool ok = driver.parseAllSources();
    auto compilation = driver.createCompilation();
    ok &= driver.reportCompilation(*compilation, /* quiet */ false);

    // Generate the Json output file.
    JsonWriter writer;
    writer.setPrettyPrint(true);

    ASTSerializer serializer(*compilation, writer);
    serializer.serialize(compilation->getRoot());

    std::string_view jsonView = writer.view();
    size_t lastBracketPos = jsonView.find_last_of('}');

    if (lastBracketPos != std::string::npos)
    {
        std::string validJson = std::string(jsonView.substr(0, lastBracketPos + 1));
        file << validJson;
    }
    else
    {
        std::cerr << "Error: Invalid JSON output" << std::endl;
        return 4;
    }
    file.close();

    return ok ? 0 : 3;
}