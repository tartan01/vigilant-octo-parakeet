package com.signal.console;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

/**
 * SIGNAL Admin Console — typical Java-web back office.
 *
 * Layering (1:1 with the Python implementation):
 *   web/*          @RestController   -> membersite/server.py
 *   service/*      @Service          -> membersite/console.py
 *   repository/*   @Repository(JDBC) -> membersite/store.py
 *
 * Run:  mvn spring-boot:run                        (H2, zero install)
 *       mvn spring-boot:run -Dspring-boot.run.profiles=mysql   (shared MySQL)
 */
@SpringBootApplication
@ConfigurationPropertiesScan
public class SignalConsoleApplication {

    public static void main(String[] args) {
        SpringApplication.run(SignalConsoleApplication.class, args);
    }
}
