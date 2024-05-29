#include "slang/ast/Compilation.h"
#include "slang/driver/Driver.h"
#include "slang/util/VersionInfo.h"
#include "slang/ast/ASTSerializer.h"
#include "slang/text/Json.h"
#include "slang/ast/symbols/CompilationUnitSymbols.h"

#include <iostream>
#include <fstream>

using namespace slang;
using namespace slang::driver;
using namespace slang::ast;

int main(int argc, char** argv) {

    std::ofstream file;
    file.open("output.json");

    Driver driver;
    driver.addStandardArgs();

    std::optional<bool> showHelp;
    std::optional<bool> showVersion;
    driver.cmdLine.add("-h,--help", showHelp, "Display available options");
    driver.cmdLine.add("--version", showVersion, "Display version information and exit");

    if (!driver.parseCommandLine(argc, argv))
        return 1;

    if (showHelp == true) {
        printf("%s\n", driver.cmdLine.getHelpText("slang SystemVerilog compiler").c_str());
        return 0;
    }

    if (showVersion == true) {
        printf("slang version %d.%d.%d+%s\n", VersionInfo::getMajor(),
            VersionInfo::getMinor(), VersionInfo::getPatch(),
            std::string(VersionInfo::getHash()).c_str());
        return 0;
    }

    if (!driver.processOptions())
        return 2;

    bool ok = driver.parseAllSources();

    auto compilation = driver.createCompilation();
    ok &= driver.reportCompilation(*compilation, /* quiet */ false);
    
    JsonWriter writer;
    writer.setPrettyPrint(true);

    ASTSerializer serializer(*compilation, writer);
    serializer.serialize(compilation->getRoot());

    file << writer.view().data();

    file.close();

    return ok ? 0 : 3;
}